import datetime
import os
from sacred.dependencies import get_digest


T1 = datetime.datetime(1999, 5, 4, 3, 2, 1)
T2 = datetime.datetime(1999, 5, 5, 5, 5, 5)
T3 = datetime.datetime(1999, 5, 5, 5, 10, 5)


def sample_run():
    exp = {'name': 'test_exp',
           'sources': [],
           'doc': '',
           'base_dir': os.path.join(os.path.dirname(__file__), '..', '..'),
           'dependencies': ['sacred==0.7b0']}
    host = {'hostname': 'test_host',
            'cpu_count': 1,
            'python_version': '3.4',
            'cpu': 'Intel',
            'os': ['Linux', 'Ubuntu']}
    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    command = 'run'
    meta_info = {'comment': 'test run'}
    dummy_run_dict = {
        '_id': 'FEDCBA9876543210',
        'ex_info': exp,
        'command': command,
        'host_info': host,
        'start_time': T1,
        'config': config,
        'meta_info': meta_info,
    }

    filename = 'setup.py'
    md5 = get_digest(filename)
    dummy_run_dict['ex_info']['sources'] = [[filename, md5]]
    return dummy_run_dict
