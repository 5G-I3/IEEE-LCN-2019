#!/bin/bash
#
# Copyright (C) 2019 Freie Universität berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

RUNNING_EXPERIMENT_FILE=${RUNNING_EXPERIMENT_FILE:-${SCRIPT_DIR}/running_experiment.txt}

SINK=${SINK:-55}
SITE=${SITE:-lille}
NETWORK=${NETWORK:-${SCRIPT_DIR}/../../results/m3-55xc7297640.edgelist.gz}
CHANNEL=${CHANNEL:-26}

AGGRESSIVE_REASS=${AGGRESSIVE_REASS:-0}
REASS_TIMEOUT=${REASS_TIMEOUT:-10000000}
RBUF_SIZE_SOURCE=${RBUF_SIZE_SOURCE:-1}
RBUF_SIZE_SINK=${RBUF_SIZE_SOURCE:-16}
VRB_SIZE=${VRB_SIZE:-16}

RUNS=${RUNS:-3}
DELAY=${DELAY:-10000}
COUNT=${COUNT:-100}
EXP_DURATION=${EXP_DURATION:-2880}

MODE=(reass fwd)
DATA_LEN=(656 16 1232 368 944 80 176 272 464 560 752 848 1040 1136)

. ${SCRIPT_DIR}/ssh-agent.cfg
if [ -z "${SSH_AGENT_PID}" ] || ! ps -p ${SSH_AGENT_PID} > /dev/null; then
    ssh-agent > ${SCRIPT_DIR}/ssh-agent.cfg
    . ${SCRIPT_DIR}/ssh-agent.cfg
fi

if ! ssh-add -l &> /dev/null; then
    ssh-add
fi

if [ -n "${RUN_DURATION}" ]; then
    RUN_DURATION="--run-duration ${RUN_DURATION}"
fi

if [ -f "${NETWORK}" ]; then
    NETWORK="-f ${NETWORK}"
fi

for run in $(seq ${RUNS}); do
    echo "========= RUN $(( run )) ========="
    for (( m=0; m < ${#MODE[@]}; m++ )); do
        REFLASH="-r"
        for (( l=0; l < ${#DATA_LEN[@]}; l++ )); do
            echo "--------- (${MODE[$m]}, ${DATA_LEN[$l]}, ${COUNT}, ${DELAY}) ---------"
            AGGRESSIVE_REASS=${AGGRESSIVE_REASS} \
            RBUF_SIZE_SOURCE=${RBUF_SIZE_SOURCE} \
            RBUF_SIZE_SINK=${RBUF_SIZE_SINK} \
            VRB_SIZE=${VRB_SIZE} \
            REASS_TIMEOUT=${REASS_TIMEOUT} \
            ${SCRIPT_DIR}/run_experiment.py \
                    $(cat ${RUNNING_EXPERIMENT_FILE} 2> /dev/null) \
                    ${NETWORK} ${REFLASH} -d ${EXP_DURATION} -S ${SITE} \
                    -l ${DATA_LEN[$l]} -W ${DELAY} -c ${COUNT} \
                    ${RUN_DURATION} ${SINK} ${MODE[$m]}
            FAILED=$?
            REFLASH=""
            if [ ${FAILED} -ne 0 ]; then
                ((l--));
            fi
        done
        if [ ${FAILED} -ne 0 ]; then
            ((m--));
        fi
    done
done

