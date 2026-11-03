# Local run notes

The first local MPI attempt used MPICH/libfabric's default interface and stopped at `MPI_Finalize` when it selected `en0`. A two-rank smoke test confirmed `FI_PROVIDER=sockets`; all final MPI result folders were then rerun with that provider. The provider is recorded in `environment.txt`.

While updating the running shell script's metadata, an unintended duplicate p=8 Allgatherv run started. It was terminated after the intended 42 graphs × 4 process counts × 2 communication modes × 2 MPI implementations had all written complete result folders. The duplicate did not replace the completed result files. The four independent MPI validation reports were then run to completion, each passing 168/168 checks, and `mpi.complete` was written. Hybrid was run afterward and both Hybrid validation reports passed 420/420. The `hybrid.complete` marker records the completed fixed-graph matrix.

Raw `timings.csv` files retain all five measured solves for every final configuration. The interrupted launcher log is retained locally but is not a benchmark row.
