
"""
Slotted ALOHA Simulator

This script runs a discrete-time simulation of Slotted ALOHA on a single device
to demonstrate successes, collisions and retransmission/backoff behavior.

Features:
- Configurable number of nodes and slots
- Packet arrivals modeled per-slot with probability `arrival_prob`
- Per-packet retransmission attempts with binary exponential backoff
- Per-slot logging and final summary (throughput, collision rate, delays)

Run with defaults:
  python slotted_aloha_sim.py

Or view help:
  python slotted_aloha_sim.py --help
"""
import random
import statistics
import time
from collections import deque

# --- Configuration (no CLI) ---
# Edit these values to run the simulation without command-line args.
NODES = 10
SLOTS = 2000
ARRIVAL_PROB = 0.02
MAX_BACKOFF = 6
VERBOSE = False
# ------------------------------


class Packet:
    def __init__(self, created_slot):
        self.created_slot = created_slot
        self.attempts = 0
        self.backoff = 0


class Node:
    def __init__(self, node_id):
        self.id = node_id
        self.queue = deque()

    def has_ready(self):
        return len(self.queue) > 0 and self.queue[0].backoff == 0

    def schedule_new_packet(self, slot):
        self.queue.append(Packet(created_slot=slot))

    def on_collision(self, slot, max_backoff_exp=5):
        pkt = self.queue[0]
        pkt.attempts += 1
        exp = min(pkt.attempts, max_backoff_exp)
        window = 2 ** exp
        pkt.backoff = random.randint(1, window - 1) if window > 1 else 0

    def on_success(self):
        pkt = self.queue.popleft()
        return pkt

    def tick_backoff(self):
        if len(self.queue) == 0:
            return
        if self.queue[0].backoff > 0:
            self.queue[0].backoff -= 1


def simulate_slots(num_nodes=10, num_slots=1000, arrival_prob=0.02, max_backoff_exp=6, verbose=False):
    nodes = [Node(i) for i in range(num_nodes)]

    stats = {
        'slots': num_slots,
        'successes': 0,
        'collisions': 0,
        'empty': 0,
        'delays': [],
    }

    for slot in range(1, num_slots + 1):
        # New arrivals
        for n in nodes:
            if random.random() < arrival_prob:
                n.schedule_new_packet(slot)

        # Collect transmitters (those with ready packets and backoff==0)
        transmitters = [n for n in nodes if n.has_ready()]

        if len(transmitters) == 0:
            stats['empty'] += 1
            if verbose:
                print(f"Slot {slot:4d}: <empty>")
        elif len(transmitters) == 1:
            # success
            n = transmitters[0]
            pkt = n.on_success()
            stats['successes'] += 1
            delay = slot - pkt.created_slot + 1
            stats['delays'].append(delay)
            if verbose:
                print(f"Slot {slot:4d}: Node {n.id} TRANSMIT -> SUCCESS (delay={delay})")
        else:
            # collision
            stats['collisions'] += 1
            if verbose:
                ids = ','.join(str(n.id) for n in transmitters)
                print(f"Slot {slot:4d}: Nodes {ids} TRANSMIT -> COLLISION")
            for n in transmitters:
                n.on_collision(slot, max_backoff_exp=max_backoff_exp)

        # advance backoff counters at end of slot
        for n in nodes:
            n.tick_backoff()

    # Summary
    throughput = stats['successes'] / stats['slots']
    collision_rate = stats['collisions'] / (stats['slots'] - stats['empty']) if (stats['slots'] - stats['empty']) > 0 else 0
    avg_delay = statistics.mean(stats['delays']) if stats['delays'] else float('nan')

    summary = {
        'slots': stats['slots'],
        'successes': stats['successes'],
        'collisions': stats['collisions'],
        'empty_slots': stats['empty'],
        'throughput_per_slot': throughput,
        'collision_rate_given_activity': collision_rate,
        'avg_delay_slots': avg_delay,
    }

    return summary


def pretty_print_summary(s):
    print('\n=== Slotted ALOHA Simulation Summary ===')
    print(f"Slots: {s['slots']}")
    print(f"Successes: {s['successes']}")
    print(f"Collisions: {s['collisions']}")
    print(f"Empty slots: {s['empty_slots']}")
    print(f"Throughput (successful slots / total slots): {s['throughput_per_slot']:.4f}")
    print(f"Collision rate (given activity): {s['collision_rate_given_activity']:.4f}")
    print(f"Average delay (slots): {s['avg_delay_slots']:.2f}")
    print('=======================================\n')


def run_from_config():
    """Run simulation using static configuration values defined at the top.

    This removes the CLI and makes the script suitable for running as a demo
    or in environments where editing the file is preferred over passing flags.
    """
    start = time.time()
    summary = simulate_slots(num_nodes=NODES, num_slots=SLOTS, arrival_prob=ARRIVAL_PROB, max_backoff_exp=MAX_BACKOFF, verbose=VERBOSE)
    end = time.time()

    pretty_print_summary(summary)
    print(f"Simulation time: {end - start:.3f}s")


if __name__ == '__main__':
    run_from_config()
