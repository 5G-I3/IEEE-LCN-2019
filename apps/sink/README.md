# Sink application
This application implements the sink for the experiments for the paper.
It starts as an IPv6 router and opens a UDP socket listening on port 6383 (can
be overridden by define `SINK_PORT`).

## Compile-time configuration
There are some compile-time configurations that are exposed to the via
environment variables

- `MODE`: (default: `reass`) Can be either `reass` (for hop-wise reassembly) or
  `fwd` (for fragment forwarding)
- `VRB_SIZE`: (default: 16) The size of the virtual reassembly buffer (with mode
  `fwd`)
- `RBUF_SIZE_SINK`: (default: 16) The size of the sink's reassembly buffer
- `REASS_TIMEOUT`: (default: 10000000) Reassembly timeout in microseconds
- `AGGRESSIVE_REASS`: (default: 0) (De-)activate aggressive reassembly (override
  reassembly buffer when full)

## Usage
Once the node is up a global address can be configured using

```
ifconfig <if> add <addr>
```
