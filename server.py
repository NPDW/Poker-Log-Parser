"""
PokerNow Logs Web Based

Currently static because effort.
"""
import argparse
import concurrent
import concurrent.futures
import csv
import json
import logging
import os

import tornado
import tornado.web
from  tornado import template

from game_tracker import GameTracker
from log_parser import LogParser
from stats_parser import StatsParser
from utils import Utils


log = logging.getLogger('poker_track')

parser = argparse.ArgumentParser(description='Poker Now Server Log Tracker.')
parser.add_argument('-p', '--port', type=int, default=None,
                  help='Port to listen on. Default: 80 / 443')
parser.add_argument('-g', '--game-id', type=str, default='2VQEY-Vn6ggeXBtg7mUkXY_Dd',
                  help='Game Id')
cmd_args = parser.parse_args()


GAME_ID = 'YiGSaUBmpPnB2pB8prARt-QhR'


class GameManager(object):
   stats = None
   hands = {}

   def __init__(self, game_id):
      stats_file = 'stats/%s.csv' % GAME_ID
      if os.path.isfile(stats_file):
         with open(stats_file, 'r') as f:
            data = f.read()
            # self.stats = data

   def get_formatted(self, dec_places=4):
      formatted_stats = {"stats": {}, "details": {}}

      # Rounding
      for stat_name, stat in self.stats.items():
         formatted_stats['stats'][stat_name] = {"values": {}}

         for name, val in stat.items():
            formatted_stats['stats'][stat_name]['values'][name] = round(val, dec_places)

      # Add docstring
      for stat in StatsParser.STAT_CLASSES:
         stat_class = stat({})
         formatted_stats['stats'][stat_class.__name__]['desc'] = stat_class.__doc__

      # Add overall stats
      formatted_stats['details']['hands_played'] = {
         "title": "Hands Played",
         "sub_title": "Current Session",
         "value": len(self.hands)
      }

      total_players = set()
      for stat_name, stat in self.stats.items():
         for player in stat:
            if player not in total_players:
               total_players.add(player)

      # Add overall stats
      formatted_stats['details']['players_tracked'] = {
         "title": "Players Tracked",
         "sub_title": "Current Session",
         "value": len(total_players)
      }

      return formatted_stats



game_manager = GameManager(GAME_ID)



class HelloWorldHandler(tornado.web.RequestHandler):
   """Simplest Hello World handler"""
   async def get(self):
      if game_manager.stats:
         # self.write(json.dumps(game_manager.stats, indent=4))
         loader = template.Loader("templates")
         formatted_stats = game_manager.get_formatted()
         self.write(loader.load("base2.html").generate(stats=formatted_stats))

      else:
         self.write('Nothing yet, stay calm Dan')
      # self.write('Hello, world\nExample API is up!\n')


class Server(object):
   def __init__(self, log, port):
      self.log = log
      self.app = self.make_app()
      self.app.listen(port=port)
      self.log.info('event="api-started"')

      self.ioloop = tornado.ioloop.IOLoop.current()
      # Testing frontend
      # pc = tornado.ioloop.PeriodicCallback(self.periodic_callback, 20 * 1000,
      #                                      jitter=0.1)
      # pc.start()
      self.ioloop.add_callback(self.periodic_callback)
      self.ioloop.start()

   async def periodic_callback(self):
      """Update logs, internal json logs and stats"""
      self.log.info('event="calling-logs"')
      await self.app.game_tracker.listen()
      if self.app.game_tracker.updates:
         self.log.info('event="applying-updates"')
         await self.app.log_parser.parse_file()
         self.app.stats_parser.parse_file()
         global game_manager
         game_manager.stats = self.app.stats_parser.stats
         game_manager.hands = self.app.log_parser.hands
      self.log.info('event="finished-calling-logs"')




   def make_app(self):
      app = tornado.web.Application([
         # Additional endpoints to test the service is up and running.
         (r"/stats", HelloWorldHandler),
      ])
      app.game_tracker = GameTracker(GAME_ID)
      app.stats_parser = StatsParser(GAME_ID)
      app.log_parser = LogParser(GAME_ID)

      return app


def main():
   log_format = 'time="%(asctime)-15s" level=%(levelname)-7s %(message)s'
   logging.basicConfig(
      level=logging.INFO,
      format=log_format)

   if not cmd_args.port:
      cmd_args.port = 80

   log.info('=' * 51)
   log.info('{:^51}'.format('Starting PokerNow Stats'))
   log.info(' '.join(['*'] * 25))

   for key, value in vars(cmd_args).items():
      log.info('{!s:>24s} = {!s:<24}'.format(key, value))

   log.info('=' * 51)

   log.info('event="api-starting"')


   server = Server(log=log, port=cmd_args.port)

   # app = server.make_app()
   # app.listen(cmd_args.port)
   # log.info('event="api-started"')


   # tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
   main()
