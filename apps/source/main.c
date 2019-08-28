/*
 * Copyright (C) 2019 Freie Universität Berlin
 *
 * This file is subject to the terms and conditions of the GNU Lesser
 * General Public License v2.1. See the file LICENSE in the top level
 * directory for more details.
 */

/**
 * @{
 * @file
 * @author      Martine S. Lenders <m.lenders@fu-berlin.de>
 * @}
 */

#include <stdint.h>
#include <stdio.h>

#include "byteorder.h"
#include "mutex.h"
#include "net/ipv6/addr.h"
#include "net/sock/udp.h"
#include "random.h"
#include "shell.h"
#include "thread.h"
#include "timex.h"
#include "xtimer.h"

#ifndef SINK_PORT
#define SINK_PORT           (6383U)
#endif

#ifndef SOURCE_BUFSIZE
#define SOURCE_BUFSIZE      (1232U)
#endif

#define SOURCE_BUF_OFFSET   (48U)

typedef struct {
    sock_udp_ep_t remote;
    size_t data_len;
    uint32_t num;
    uint32_t delay_min;
    uint32_t delay_max;
} _source_config_t;

static char _source_stack[THREAD_STACKSIZE_MAIN];
static mutex_t _source_started = MUTEX_INIT_LOCKED;
static kernel_pid_t _source_pid = KERNEL_PID_UNDEF;

static int _source_cmd(int argc, char **argv);

static network_uint16_t _source_buf[SOURCE_BUFSIZE / sizeof(network_uint16_t)];
static const shell_command_t _shell_commands[] = {
    { "source", "send data over UDP periodically", _source_cmd },
    { NULL, NULL, NULL }
};

int main(void)
{
    char line_buf[SHELL_DEFAULT_BUFSIZE];

    /* start shell */
    puts("All up, running the shell now");
    shell_run(_shell_commands, line_buf, SHELL_DEFAULT_BUFSIZE);

    /* should be never reached */
    return 0;
}

static void _source_usage(char *cmd)
{
    printf("usage: %s <addr> <port> <data_len> <num> <delay mean [min] in ms> "
           "[delay max in ms]\n", cmd);
}

static void *_source_thread(void *arg)
{
    _source_config_t config = *((_source_config_t *)arg);
    sock_udp_t sock;
    xtimer_ticks32_t last_wakeup;
    uint16_t id = 0;

    mutex_unlock(&_source_started);
    memset(&_source_buf, 0, sizeof(_source_buf));

    printf("start sending: data_len: %u\n", (size_t)config.data_len);
    printf("               num: %u\n", (unsigned)config.num);
    printf("               delay min: %u\n",
           (unsigned)config.delay_min);
    printf("               delay max: %u\n",
           (unsigned)config.delay_max);
    if (sock_udp_create(&sock, NULL, &config.remote, 0) < 0) {
        puts("Error creating UDP sock");
        goto error_out;
    }
    last_wakeup = xtimer_now();
    for (unsigned i = 0; i < config.num; i++, id++) {
        int res;

        xtimer_periodic_wakeup(
            &last_wakeup,
            random_uint32_range(config.delay_min,
                                config.delay_max));
        for (unsigned j = 0; j < (config.data_len / sizeof(network_uint16_t));
             j += SOURCE_BUF_OFFSET) {
            _source_buf[j] = byteorder_htons(id);
        }
        if ((res = sock_udp_send(&sock, _source_buf,
                                 config.data_len, NULL)) < 0) {
            printf("err;%04x;%d\n", id, -res);
        }
        else {
            printf("out;%04x\n", id);
        }
    }
    sock_udp_close(&sock);
error_out:
    _source_pid = KERNEL_PID_UNDEF;
    mutex_lock(&_source_started);
    return NULL;
}

static int _source_cmd(int argc, char **argv)
{
    static _source_config_t _source_config = { .remote = SOCK_IPV6_EP_ANY };

    if (_source_pid > KERNEL_PID_UNDEF) {
        puts("command already running");
        return 1;
    }

    if (argc < 6) {
        _source_usage(argv[0]);
        return 1;
    }

    if (argc > 6) {
        _source_config.delay_min = atoi(argv[5]) * US_PER_MS;
        _source_config.delay_max = atoi(argv[6]) * US_PER_MS;
    }
    else {
        const uint32_t delay_mean = atoi(argv[5]) * US_PER_MS;
        const uint32_t delay_var = delay_mean / 2;
        _source_config.delay_min = delay_mean - delay_var;
        _source_config.delay_max = delay_mean + delay_var;
    }

    _source_config.remote.port = atoi(argv[2]);
    _source_config.data_len = atoi(argv[3]);
    _source_config.num = atoi(argv[4]);
    if ((_source_config.remote.port == 0) || (_source_config.data_len == 0) ||
        (_source_config.data_len > sizeof(_source_buf)) ||
        (_source_config.num == 0U) ||
        (_source_config.delay_min == 0U) || (_source_config.delay_max == 0U) ||
        (ipv6_addr_from_str((ipv6_addr_t *)&_source_config.remote.addr.ipv6,
                            argv[1]) == NULL)) {
        _source_usage(argv[0]);
        return 1;
    }
    _source_pid = thread_create(_source_stack, sizeof(_source_stack),
                                THREAD_PRIORITY_MAIN - 1,
                                THREAD_CREATE_STACKTEST,
                                _source_thread, &_source_config, "source");
    mutex_lock(&_source_started);
    return 0;
}
