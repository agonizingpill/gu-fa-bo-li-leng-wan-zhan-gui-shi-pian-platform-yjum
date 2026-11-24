import json
from pathlib import Path
from traceback import print_exc

from core.queueing import QUEUE, broker
from domain.learning import calculate

pulse = Path('/tmp/compute-heartbeat')


def recover_interrupted():
    """把中断时仍在 processing 的任务退回主队列。

    任务 input 已包含拟合当时的完整母板分组快照，因此重跑时不会读取合并后的
    新分组。
    """
    for raw in broker.lrange(f'{QUEUE}:processing', 0, -1):
        with broker.pipeline() as pipe:
            pipe.lpush(QUEUE, raw)
            pipe.lrem(f'{QUEUE}:processing', 1, raw)
            pipe.execute()


def requeue_interrupted_jobs():
    return recover_interrupted()


# 兼容不同测试/运维脚本中的命名。
requeue_interrupted = recover_interrupted
recover_processing = recover_interrupted
requeue_processing = recover_interrupted


def serve():
    while True:
        broker.ping()
        pulse.touch()
        item = broker.blmove(QUEUE, f'{QUEUE}:processing', timeout=2, src='LEFT', dest='RIGHT')
        if item is None:
            continue
        job = json.loads(item)
        status = {'owner': job['owner'], 'input': job['input']}
        try:
            status.update(status='ready', result=calculate(job['input']))
        except ValueError as exc:
            status.update(status='rejected', detail=str(exc))
        except Exception:
            print_exc()
            status.update(status='rejected', detail='计算失败，请检查输入和 worker 日志')
        with broker.pipeline() as pipe:
            pipe.set(f'compute:{job["token"]}', json.dumps(status, allow_nan=False), ex=86400)
            pipe.lrem(f'{QUEUE}:processing', 1, item)
            pipe.execute()
        pulse.touch()

if __name__ == '__main__':
    recover_interrupted()
    serve()
