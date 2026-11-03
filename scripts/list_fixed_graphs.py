"""Print fixed-graph names in the same order as generate_scaling_graphs.py."""
from generate_scaling_graphs import FAMILIES, SERIAL_AVERAGE_DEGREES, SERIAL_VERTICES

for name in ("google", "uniform", "hub"):
    print(name)
for family in FAMILIES:
    print(f"synthetic_{family}")
    for vertices in SERIAL_VERTICES:
        for degree in SERIAL_AVERAGE_DEGREES:
            print(f"grid_{family}_n{vertices}_d{degree}")
for family in FAMILIES:
    print(f"strong_{family}")
