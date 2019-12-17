import os
from PIL import Image
import numpy as np
from gym_pcgrl.envs.probs.problem import Problem
from gym_pcgrl.envs.helper import calc_certain_tile, calc_num_regions
from gym_pcgrl.envs.probs.sokoban.engine import State,BFSAgent,AStarAgent

"""
Generate a fully connected Sokoban(https://en.wikipedia.org/wiki/Sokoban) level that can be solved
"""
class SokobanProblem(Problem):
    """
    The constructor is responsible of initializing all the game parameters
    """
    def __init__(self):
        super().__init__()
        self._width = 5
        self._height = 5
        self._prob = {"empty":0.45, "solid":0.4, "player": 0.05, "crate": 0.05, "target": 0.05}
        self._border_tile = "solid"

        self._max_crates = 3

        self._target_solution = 20

        self._rewards = {
            "player": 5,
            "crate": 5,
            "target": 5,
            "regions": 5,
            "ratio": 1,
            "dist-win": 0.01,
            "sol-length": 1
        }

    """
    Get a list of all the different tile names

    Returns:
        string[]: that contains all the tile names
    """
    def get_tile_types(self):
        return ["empty", "solid", "player", "crate", "target"]

    """
    Adjust the parameters for the current problem

    Parameters:
        width (int): change the width of the problem level
        height (int): change the height of the problem level
        probs (dict(string, float)): change the probability of each tile
        intiialization, the names are "empty", "solid", "player", "crate", "target"
        max_crates or max_targets (int): the max number of crates or target both
        suppose to be the same value so setting one is enough
        target_solution (int): the target solution length that the level is considered a success if reached
        rewards (dict(string,float)): the weights of each reward change between the new_stats and old_stats
    """
    def adjust_param(self, **kwargs):
        super().adjust_param(**kwargs)

        self._max_crates = kwargs.get('max_crates', self._max_crates)
        self._max_crates = kwargs.get('max_targets', self._max_crates)

        self._target_solution = kwargs.get('min_solution', self._target_solution)

        rewards = kwargs.get('rewards')
        if rewards is not None:
            for t in rewards:
                if t in self._rewards:
                    self._rewards[t] = rewards[t]

    """
    Private function that runs the game on the input level

    Parameters:
        map (string[][]): the input level to run the game on

    Returns:
        float: how close you are to winning (0 if you win)
        int: the solution length if you win (0 otherwise)
    """
    def _run_game(self, map):
        gameCharacters=" #@$."
        string_to_char = dict((s, gameCharacters[i]) for i, s in enumerate(self.get_tile_types()))
        lvlString = ""
        for x in range(self._width+2):
            lvlString += "#"
        lvlString += "\n"
        for i in range(len(map)):
            for j in range(len(map[i])):
                string = map[i][j]
                if j == 0:
                    lvlString += "#"
                lvlString += string_to_char[string]
                if j == self._width-1:
                    lvlString += "#\n"
        for x in range(self._width+2):
            lvlString += "#"
        lvlString += "\n"

        state = State()
        state.stringInitialize(lvlString.split("\n"))

        aStarAgent = AStarAgent()
        bfsAgent = BFSAgent()

        sol,solState,iters = bfsAgent.getSolution(state, 5000)
        if solState.checkWin():
            return 0, sol
        sol,solState,iters = aStarAgent.getSolution(state, 1, 5000)
        if solState.checkWin():
            return 0, sol
        sol,solState,iters = aStarAgent.getSolution(state, 0.5, 5000)
        if solState.checkWin():
            return 0, sol
        sol,solState,iters = aStarAgent.getSolution(state, 0.25, 5000)
        if solState.checkWin():
            return 0, sol
        sol,solState,iters = aStarAgent.getSolution(state, 0, 5000)
        if solState.checkWin():
            return 0, sol
        return solState.getHeuristic(), []

    """
    Get the current stats of the map

    Returns:
        dict(string,any): stats of the current map to be used in the reward, episode_over, debug_info calculations.
        The used status are "player": number of player tiles, "crate": number of crate tiles,
        "target": number of target tiles, "reigons": number of connected empty tiles,
        "dist-win": how close to the win state, "sol-length": length of the solution to win the level
    """
    def get_stats(self, map):
        map_stats = {
            "player": calc_certain_tile(map, ["player"]),
            "crate": calc_certain_tile(map, ["crate"]),
            "target": calc_certain_tile(map, ["target"]),
            "regions": calc_num_regions(map, ["empty","player","crate","target"]),
            "dist-win": self._width * self._height * (self._width + self._height),
            "solution": []
        }
        if map_stats["player"] == 1 and map_stats["crate"] == map_stats["target"] and map_stats["crate"] > 0 and map_stats["regions"] == 1:
                map_stats["dist-win"], map_stats["solution"] = self._run_game(map)
        return map_stats

    """
    Get the current game reward between two stats

    Parameters:
        new_stats (dict(string,any)): the new stats after taking an action
        old_stats (dict(string,any)): the old stats before taking an action

    Returns:
        float: the current reward due to the change between the old map stats and the new map stats
    """
    def get_reward(self, new_stats, old_stats):
        #longer path is rewarded and less number of regions is rewarded
        rewards = {
            "player": 0,
            "crate": 0,
            "target": 0,
            "regions": 0,
            "ratio": 0,
            "dist-win": 0,
            "sol-length": 0
        }
        #calculate the player reward
        rewards["player"] = old_stats["player"] - new_stats["player"]
        if rewards["player"] > 0 and new_stats["player"] == 0:
            rewards["player"] *= -1
        elif rewards["player"] < 0 and new_stats["player"] == 1:
            rewards["player"] *= -1
        #calculate crate reward (between 1 and max_crates)
        rewards["crate"] = old_stats["crate"] - new_stats["crate"]
        if rewards["crate"] < 0 and old_stats["crate"] == 0:
            rewards["crate"] *= -1
        elif new_stats["crate"] >= 1 and new_stats["crate"] <= self._max_crates and\
                old_stats["crate"] >= 1 and old_stats["crate"] <= self._max_crates:
            rewards["crate"] = 0
        #calculate target reward (between 1 and max_crates)
        rewards["target"] = old_stats["target"] - new_stats["target"]
        if rewards["target"] < 0 and old_stats["target"] == 0:
            rewards["target"] *= -1
        elif new_stats["target"] >= 1 and new_stats["target"] <= self._max_crates and\
                old_stats["target"] >= 1 and old_stats["target"] <= self._max_crates:
            rewards["target"] = 0
        #calculate regions reward
        rewards["regions"] = old_stats["regions"] - new_stats["regions"]
        if new_stats["regions"] == 0 and old_stats["regions"] > 0:
            rewards["regions"] = -1
        #calculate ratio rewards
        new_ratio = abs(new_stats["crate"] - new_stats["target"])
        old_ratio = abs(old_stats["crate"] - old_stats["target"])
        rewards["ratio"] = old_ratio - new_ratio
        #calculate distance remaining to win
        rewards["dist-win"] = old_stats["dist-win"] - new_stats["dist-win"]
        #calculate solution length (more than min solution)
        rewards["sol-length"] = len(new_stats["solution"]) - len(old_stats["solution"])
        #calculate the total reward
        return rewards["player"] * self._rewards["player"] +\
            rewards["crate"] * self._rewards["crate"] +\
            rewards["target"] * self._rewards["target"] +\
            rewards["regions"] * self._rewards["regions"] +\
            rewards["ratio"] * self._rewards["ratio"] +\
            rewards["dist-win"] * self._rewards["dist-win"] +\
            rewards["sol-length"] * self._rewards["sol-length"]

    """
    Uses the stats to check if the problem ended (episode_over) which means reached
    a satisfying quality based on the stats

    Parameters:
        new_stats (dict(string,any)): the new stats after taking an action
        old_stats (dict(string,any)): the old stats before taking an action

    Returns:
        boolean: True if the level reached satisfying quality based on the stats and False otherwise
    """
    def get_episode_over(self, new_stats, old_stats):
        return len(new_stats["solution"]) >= self._target_solution

    """
    Get any debug information need to be printed

    Parameters:
        new_stats (dict(string,any)): the new stats after taking an action
        old_stats (dict(string,any)): the old stats before taking an action

    Returns:
        dict(any,any): is a debug information that can be used to debug what is
        happening in the problem
    """
    def get_debug_info(self, new_stats, old_stats):
        return {
            "player": new_stats["player"],
            "crate": new_stats["crate"],
            "target": new_stats["target"],
            "regions": new_stats["regions"],
            "dist-win": new_stats["dist-win"],
            "sol-length": len(new_stats["solution"])
        }

    """
    Get an image on how the map will look like for a specific map

    Parameters:
        map (string[][]): the current game map

    Returns:
        Image: a pillow image on how the map will look like using sokoban graphics
    """
    def render(self, map):
        if self._graphics == None:
            self._graphics = {
                "empty": Image.open(os.path.dirname(__file__) + "/sokoban/empty.png").convert('RGBA'),
                "solid": Image.open(os.path.dirname(__file__) + "/sokoban/solid.png").convert('RGBA'),
                "player": Image.open(os.path.dirname(__file__) + "/sokoban/player.png").convert('RGBA'),
                "crate": Image.open(os.path.dirname(__file__) + "/sokoban/crate.png").convert('RGBA'),
                "target": Image.open(os.path.dirname(__file__) + "/sokoban/target.png").convert('RGBA')
            }
        return super().render(map)
