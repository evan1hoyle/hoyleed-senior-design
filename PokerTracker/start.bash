#!/bin/bash


tmux new-session -d -s work 'python3 PokerTracker/flop.py -v'
tmux split-window -h 'python3 PokerTracker/TurnTracker.py'
tmux split-window -v 'python3 PokerTracker/arduino/knock.py'
cd PokerTracker
tmux split-window -v 'python3 -m http.server 8000'


tmux attach-session -t work