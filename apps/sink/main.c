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
#include "net/ipv6/addr.h"
#include "net/sock/udp.h"
#include "shell.h"
#include "thread.h"

#ifndef SINK_PORT
#define SINK_PORT       (6383U)
#endif

#ifndef SINK_BUFSIZE
#define SINK_BUFSIZE    (1232U)
#endif

static char _sink_stack[THREAD_STACKSIZE_DEFAULT];
static network_uint16_t _sink_buf[SINK_BUFSIZE / sizeof(network_uint16_t)];

static void *_sink_thread(void *args)
{
    sock_udp_ep_t local = SOCK_IPV6_EP_ANY;
    sock_udp_t sock;

    (void)args;
    local.port = SINK_PORT;
    if (sock_udp_create(&sock, &local, NULL, 0) < 0) {
        puts("Error creating UDP sock");
        return NULL;
    }
    printf("Opened UDP sock on port %u\n", local.port);
    while (1) {
        char addr_str[IPV6_ADDR_MAX_STR_LEN];
        sock_udp_ep_t remote;
        ssize_t res;

        if ((res = sock_udp_recv(&sock, _sink_buf, sizeof(_sink_buf),
                                 SOCK_NO_TIMEOUT,
                                 &remote)) >= (int)sizeof(_sink_buf[0])) {
            printf("in;%04x;%s;%u\n", byteorder_ntohs(_sink_buf[0]),
                   ipv6_addr_to_str(addr_str, (ipv6_addr_t *)&remote.addr.ipv6,
                                    sizeof(addr_str)), remote.port);
        }
    }
    return NULL;
}

int main(void)
{
    char line_buf[SHELL_DEFAULT_BUFSIZE];

    if (thread_create(_sink_stack, sizeof(_sink_stack),
                      THREAD_PRIORITY_MAIN - 1, THREAD_CREATE_STACKTEST,
                      _sink_thread, NULL, "sink") <= KERNEL_PID_UNDEF) {
        puts("error initializing thread");
        return 1;
    }
    /* start shell */
    puts("All up, running the shell now");
    shell_run(NULL, line_buf, SHELL_DEFAULT_BUFSIZE);

    /* should be never reached */
    return 0;
}
