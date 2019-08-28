# name of your application
APPLICATION = lcn19_sink

# If no BOARD is found in the environment, use this default:
BOARD ?= iotlab-m3

# This has to be the absolute path to the RIOT base directory:
RIOTBASE ?= $(CURDIR)/../../RIOT

# Include packages that pull up and auto-init the link layer.
# NOTE: 6LoWPAN will be included if IEEE802.15.4 devices are present
USEMODULE += gnrc_netdev_default
USEMODULE += auto_init_gnrc_netif
# Activate ICMPv6 error messages
USEMODULE += gnrc_icmpv6_error
# Specify the mandatory networking modules for IPv6 and UDP
USEMODULE += gnrc_ipv6_router_default
USEMODULE += gnrc_udp
# Queue packets when device is busy
USEMODULE += gnrc_netif_pktq
# Additional networking modules that can be dropped if not needed
USEMODULE += gnrc_icmpv6_echo
# include command to analyze packet buffer (requires DEVELHELP = 1)
USEMODULE += gnrc_pktbuf_cmd
USEMODULE += od
# include command to check stats on reassembly buffers
USEMODULE += gnrc_sixlowpan_frag_stats
# include socket API
USEMODULE += gnrc_sock_udp
# Add also the shell, some shell commands
USEMODULE += shell
USEMODULE += shell_commands
USEMODULE += ps
# include statistics modules
USEMODULE += netstats_l2
USEMODULE += netstats_ipv6

# Comment this out to disable code in RIOT that does safety checking
# which is not needed in a production environment but helps in the
# development process:
DEVELHELP ?= 1

# configure experiment mode
# - reass: hop-wise reassembly (HWR)
# - fwd: fragment forwarding (FF)
MODE ?= reass

ifeq (fwd,$(MODE))
  USEMODULE += gnrc_sixlowpan_frag_minfwd
endif

# Provide entry points for compile-time configuration via environment variables
VRB_SIZE ?= 16              # Virtual reassembly buffer size
RBUF_SIZE_SINK ?= 16        # Reassembly buffer size
REASS_TIMEOUT ?= 10000000   # Reassembly timeout (10s)
AGGRESSIVE_REASS ?= 0       # Deactivate aggressive reassembly (don't override when full)

# Expose environment variable to build docker image
DOCKER_ENV_VARS += DEVELHELP
DOCKER_ENV_VARS += MODE
DOCKER_ENV_VARS += VRB_SIZE
DOCKER_ENV_VARS += RBUF_SIZE_SINK
DOCKER_ENV_VARS += REASS_TIMEOUT
DOCKER_ENV_VARS += AGGRESSIVE_REASS

# Apply compile time configuration
CFLAGS += -DGNRC_SIXLOWPAN_FRAG_RBUF_SIZE=$(RBUF_SIZE_SINK)
CFLAGS += -DGNRC_SIXLOWPAN_FRAG_RBUF_TIMEOUT_MS=$(REASS_TIMEOUT)
CFLAGS += -DGNRC_SIXLOWPAN_FRAG_VRB_SIZE=$(VRB_SIZE)
CFLAGS += -DGNRC_SIXLOWPAN_FRAG_RBUF_AGGRESSIVE_OVERRIDE=$(AGGRESSIVE_REASS)

include $(RIOTBASE)/Makefile.include

# Set a custom channel if needed
ifneq (,$(filter cc110x,$(USEMODULE)))          # radio is cc110x sub-GHz
  DEFAULT_CHANNEL ?= 0
  CFLAGS += -DCC110X_DEFAULT_CHANNEL=$(DEFAULT_CHANNEL)
else
  ifneq (,$(filter at86rf212b,$(USEMODULE)))    # radio is IEEE 802.15.4 sub-GHz
    DEFAULT_CHANNEL ?= 5
    CFLAGS += -DIEEE802154_DEFAULT_SUBGHZ_CHANNEL=$(DEFAULT_CHANNEL)
  else                                          # radio is IEEE 802.15.4 2.4 GHz
    DEFAULT_CHANNEL ?= 26
    CFLAGS += -DIEEE802154_DEFAULT_CHANNEL=$(DEFAULT_CHANNEL)
  endif
endif
