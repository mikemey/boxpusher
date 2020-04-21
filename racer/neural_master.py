import random
from multiprocessing import Pool
from signal import signal, SIGINT
from typing import List

import neat

from best_player_keep import BestPlayerKeep, PlayerData, load_player_data
from game.racer_engine import PlayerState
from game.racer_window import RaceController, RacerWindow
from game.tracks import default_level
from neural_player import NeuralPlayer
from training_configs import load_configs
from training_dts import LIMIT_HIGH
from training_reporter import TrainingReporter

DT_IGNORE_LIMIT = LIMIT_HIGH


class NeuralMaster:
    def __init__(self):
        self.neat_config, self.training_config = load_configs()
        self.reporter = TrainingReporter(self.training_config.showcase_batch_size)
        self.best_keep = BestPlayerKeep(self.training_config)

        self.pool = None
        signal(SIGINT, self.stop)
        self.pool = Pool(processes=self.training_config.processes)

    def train(self):
        population = neat.Population(self.neat_config)
        population.add_reporter(self.reporter)
        try:
            population.run(self.eval_population)
        except Exception as ex:
            print('Training error:', ex)
        finally:
            self.stop()

    def stop(self, signal_received=None, frame=None):
        if self.pool:
            self.pool.close()
            self.pool.join()
            self.pool = None
            print('process pool closed.')
            exit(0)

    def eval_population(self, key_genomes, config: neat.config.Config):
        separated_tup = list(zip(*key_genomes))
        genomes = list(separated_tup[1])
        eval_params = [(default_level, genome, config, self.training_config) for genome in genomes]
        eval_result = self.pool.starmap(NeuralPlayer.evaluate_genome, eval_params)

        pop_result = []
        for (fitness, *game_stats), genome in zip(eval_result, genomes):
            genome.fitness = fitness
            pop_result.append((genome, config, *game_stats))
        self.best_keep.add_population_result(pop_result)

        def showcase_best():
            sorted_results = sorted(pop_result, key=lambda result: result[0].fitness, reverse=True)
            top_results = sorted_results[:self.training_config.showcase_racer_count]
            self.showcase([PlayerData(*result) for result in top_results],
                          limit=self.training_config.game_limit)

        self.reporter.run_post_batch(showcase_best)

    def showcase_from_files(self, player_files, select_random=False):
        players = [player_data for pl_file in player_files for player_data in load_player_data(pl_file)]
        if select_random:
            random.shuffle(players)
        else:
            players = sorted(players, key=lambda data: data.genome.fitness, reverse=True)
        self.showcase(players[:self.training_config.showcase_racer_count], auto_close=False)

    def showcase(self, players: List[PlayerData], limit=None, auto_close=True):
        fitness_sps_log = ['{:.0f}/{:.1f}'.format(data.genome.fitness, data.score_per_second) for data in players]
        print('Showcase: {} players (fit/sps) {}'.format(len(players), ', '.join(fitness_sps_log)))
        try:
            ShowcaseController(players, self.pool, limit, auto_close).showcase()
            print('Showcases finished, waiting {} seconds to exit...'.format(ShowcaseController.DELAY_AUTO_CLOSE_SECS))
        except Exception as e:
            msg = 'no screen available' if str(e) == 'list index out of range' else e
            print('Showcase error:', msg)


class ShowcaseController(RaceController):
    DELAY_AUTO_CLOSE_SECS = 3

    def __init__(self, players: List[PlayerData], pool: Pool, limit: int, auto_close: bool):
        super().__init__()
        self.__neural_player = [NeuralPlayer(default_level, data.genome, data.config, limit, name=data.name)
                                for data in players]
        self.__pool = pool

        self.window = RacerWindow(self, show_traces=False, show_fps=True)
        self.auto_close = auto_close
        self.seconds_to_close = self.DELAY_AUTO_CLOSE_SECS
        self.closing = False

    def showcase(self):
        self.window.start()

    def get_score_text(self):
        highest_score = max([player.score for player in self.__neural_player])
        return 'max: {:.0f}'.format(highest_score)

    def get_ranking(self):
        ranking = sorted(enumerate(self.__neural_player), key=lambda pl: pl[1].score, reverse=True)
        names, scores = '#  name\n────────────\n', 'score\n\n'
        for ix, player in ranking:
            names += '{}  {}\n'.format(ix + 1, player.name)
            scores += '{:.0f}\n'.format(player.score)
        return names, scores

    def update_player_states(self, dt):
        if self.closing or dt > DT_IGNORE_LIMIT:
            return

        if self.show_end_screen and self.auto_close:
            self.seconds_to_close -= dt
            if self.seconds_to_close < 0:
                self.window.close()
                self.closing = True
        else:
            pool_params = [(player, dt) for player in self.__neural_player]
            self.__neural_player = self.__pool.starmap(update_player_state, pool_params)
            self.show_end_screen = all([player.engine.game_over for player in self.__neural_player])

    def get_player_states(self) -> List[PlayerState]:
        return [player.get_state() for player in self.__neural_player]

    def get_player_count(self):
        return len(self.__neural_player)

    def get_end_text(self):
        if self.auto_close:
            return '', 'waiting {} seconds to exit...'.format(self.DELAY_AUTO_CLOSE_SECS), ''
        else:
            return '', ''


def update_player_state(player, dt):
    if not player.engine.game_over:
        player.next_step(dt)
    return player
