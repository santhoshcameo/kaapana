

import os
from os.path import join, exists, basename, dirname
from glob import glob
import json
import shutil
import pydicom
from pydicom.uid import generate_uid
from pathlib import Path
from shutil import copy2, move, rmtree

from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.blueprints.kaapana_global_variables import WORKFLOW_DIR
from kaapana.operators.HelperOpensearch import HelperOpensearch

class LocalModelGetInputDataOperator(LocalGetInputDataOperator):

    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf
        print('conf', conf)
        
        query = {
            "bool": {
                "must": [
                    {
                        "match_all": {}
                    },
                    {
                        "match_all": {}
                    }
                ],
                "filter": [],
                "should": [],
                "must_not": []
            }
        }

        if "tasks" in conf['workflow_form']:
            bool_should = []
            for protocol in conf['workflow_form']['tasks']:
                bool_should.append({
                    "match_phrase": {
                        "00181030 ProtocolName_keyword.keyword": {
                            "query": protocol
                        }
                    }
                })
            query["bool"]["must"].append({
                "bool": {
                    "should": bool_should,
                    "minimum_should_match": 1
                }
            })

        query["bool"]["must"].append({
            "match_phrase": {
                "00080060 Modality_keyword.keyword": {
                    "query": 'OT'
                }
            }
        })
        index = "meta-index"
        self.data_form = {
            "cohort_identifiers": HelperOpensearch.get_query_cohort(index=index, query=query, only_uids=True),
            "cohort_query": {
                "index": index
            }
        }
        self.check_modality = False # might be replaced later by an actual check...
            
        super().start(ds, **kwargs)

    def __init__(self,
                 dag,
                 name='patched-input-operator',
                 **kwargs):

        super().__init__(
            dag=dag,
            name=name,
            **kwargs
        )
