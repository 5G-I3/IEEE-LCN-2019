# Source application
This application implements the source for the experiments for the paper.
It starts as an IPv6 router.

## Compile-time configuration
There are some compile-time configurations that are exposed to the via
environment variables

- `MODE`: (default: `reass`) Can be either `reass` (for hop-wise reassembly) or
  `fwd` (for fragment forwarding)
- `VRB_SIZE`: (default: 16) The size of the virtual reassembly buffer (with mode
  `fwd`)
- `RBUF_SIZE_SOURCE`: (default: 1) The size of the forwarder's reassembly buffer
- `REASS_TIMEOUT`: (default: 10000000) Reassembly timeout in microseconds
- `FRAG_MSG_SIZE`: (default: 64) Fragmentation buffer size
- `NETIF_PKTQ_POOL_SIZE`: (default: 64) Network interface packet queue pool size
- `AGGRESSIVE_REASS`: (default: 0) (De-)activate aggressive reassembly (override
  reassembly buffer when full)

## Usage
Once the node is up a global address can be configured using

```
ifconfig <if> add <addr>
```

The default route to upstream can be configured using

```
nib route <if> default <next-hop link-local addr>
```

Once the experiment's network is set-up this way, the sending of periodic UDP
packets can be started by using

```
source <sink global address> <port> <payload length> <number of packets> <delay1> [<delay2>]
```

With `<delay1>` either being the minimum delay if `<delay2>` is provided, or
the mean of the randomized delay.
If `<delay2>` is provided it is the maximum delay.
The delay between packets is then uniquely distributed between `<delay1>` and
`<delay2>`. If `<delay2>` is not provided the delay is uniquely distributed
between 0.5×`<delay1>` and 1.5×`<delay2>`.
