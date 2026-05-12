TENSORBOARD_PATH=/gpu-nas/experiment_workspace/languoxing/AReaL-main/outputs/20260503_deepsearch/tensorboard/$MLP_TASK_ID
python -m examples.search_agent.tongyi_deepresearch.train \
    --config examples/search_agent/tongyi_deepresearch/runs/config_0430.yaml \
    stats_logger.tensorboard.path="${TENSORBOARD_PATH}"