# Minimal Slotted ALOHA (simplified)
import random, time

# config
NODES = 10
SLOTS = 2000
ARRIVAL = 0.02
MAX_EXP = 6
# maximum propagation delay (in slot units). Set to 0 for no propagation.
PROPAGATION_MAX = 0.0

def run_sim(propagation_max=0.0):
    created = [None]*NODES     # slot when packet arrived (None => no packet)
    attempts = [0]*NODES       # retry count
    backoff = [0]*NODES        # slots to wait before next try

    succ = col = empty = 0
    delays = []

    for slot in range(1, SLOTS+1):
        # new arrivals
        for i in range(NODES):
            if created[i] is None and random.random() < ARRIVAL:
                created[i] = slot
                attempts[i] = 0
                backoff[i] = 0

        # who transmits now?
        tx = [i for i in range(NODES) if created[i] is not None and backoff[i] == 0]

        if not tx:
            empty += 1
        else:
            # compute arrival intervals at receiver for each transmitter
            # a packet transmitted at integer `slot` occupies [slot + p, slot + p + 1)
            arrivals = []  # list of (node_index, start_time, end_time)
            for i in tx:
                p = random.random() * propagation_max
                start = slot + p
                end = start + 1.0
                arrivals.append((i, start, end))

            # determine collisions: if intervals overlap, those transmissions collide
            collided = set()
            success = set()

            # check pairwise overlaps
            for a in range(len(arrivals)):
                i, s1, e1 = arrivals[a]
                overlap = False
                for b in range(len(arrivals)):
                    if a == b:
                        continue
                    j, s2, e2 = arrivals[b]
                    # intervals overlap if start < other_end and other_start < end
                    if s1 < e2 and s2 < e1:
                        overlap = True
                        break
                if overlap:
                    collided.add(i)
                else:
                    success.add(i)

            # record results
            if not success and collided:
                # all transmissions overlapped -> one collision event for slot accounting
                col += 1
            else:
                # some transmissions succeeded (possibly multiple if propagation separates them)
                if collided:
                    col += len(collided)

            for i in success:
                # choose the arrival time for delay accounting
                start = next(s for (n, s, e) in arrivals if n == i)
                succ += 1
                delays.append(start - created[i] + 1)
                created[i] = None
                attempts[i] = backoff[i] = 0

            for i in collided:
                attempts[i] += 1
                exp = min(attempts[i], MAX_EXP)
                w = 2 ** exp
                backoff[i] = random.randint(1, w-1) if w > 1 else 0

        # tick down backoffs
        for i in range(NODES):
            if backoff[i] > 0:
                backoff[i] -= 1

    throughput = succ / SLOTS
    active_slots = SLOTS - empty
    coll_rate = (col / active_slots) if active_slots else 0
    avg_delay = (sum(delays) / len(delays)) if delays else float('nan')

    print(f"Slots={SLOTS}, Nodes={NODES}")
    print(f"Successes={succ}, Collisions={col}, Empty={empty}")
    print(f"Throughput={throughput:.4f}, Collision rate={coll_rate:.4f}, Avg delay={avg_delay:.2f}")
    if propagation_max and propagation_max > 0:
        print(f"Propagation max={propagation_max} slot(s) (random 0..max used)")

if __name__ == "__main__":
    t0 = time.time()
    # pass the module-level PROPAGATION_MAX by default
    run_sim(propagation_max=PROPAGATION_MAX)
    print("Time:", round(time.time()-t0, 3), "s")
