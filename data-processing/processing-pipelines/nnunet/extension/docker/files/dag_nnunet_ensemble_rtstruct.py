from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime
from nnunet.DiceEvaluationOperator import DiceEvaluationOperator
from nnunet.LocalDataorganizerOperator import LocalDataorganizerOperator
from nnunet.NnUnetOperator import NnUnetOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from nnunet.GetTaskModelOperator import GetTaskModelOperator
from nnunet.LocalSortGtOperator import LocalSortGtOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from kaapana.operators.DcmSeg2ItkOperator import DcmSeg2ItkOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.DcmStruct2Nifti import DcmStruct2Nifti
from nnunet.SegCheckOperator import SegCheckOperator

default_interpolation_order = "default"
# default_interpolation_order = "default"
default_prep_thread_count = 1
default_nifti_thread_count = 1
test_cohort_limit = 5
organ_filter = "Lung-Right,Lung-Left"

parallel_processes = 3
ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "input": {
                "title": "Input Modality",
                "default": "OT",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
            },
            "interpolation_order": {
                "title": "interpolation order",
                "default": default_interpolation_order,
                "description": "Set interpolation_order.",
                "enum": ["default", "0", "1", "2", "3"],
                "type": "string",
                "readOnly": False,
                "required": True
            },
            "inf_threads_prep": {
                "title": "Pre-processing threads",
                "type": "integer",
                "default": default_prep_thread_count,
                "description": "Set pre-processing thread count.",
                "required": True
            },
            "inf_threads_nifti": {
                "title": "NIFTI threads",
                "type": "integer",
                "description": "Set NIFTI export thread count.",
                "default": default_nifti_thread_count,
                "required": True
            },
            "inf_seg_filter": {
                "title": "SEG filter",
                "default": str(organ_filter),
                "description": "Labels to filter the predictions (eg 'spleen,liver,...')",
                "type": "string",
                "readOnly": False,
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            }
        }
    }
}

args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='nnunet-ensemble-rtstruct',
    default_args=args,
    concurrency=3,
    max_active_runs=2,
    schedule_interval=None
)

get_test_images = LocalGetInputDataOperator(
    dag=dag,
    name="nnunet-cohort",
    batch_name="nnunet-cohort",
    cohort_limit=test_cohort_limit,
    inputs=[
        {
            "opensearch-query": {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match_all": {}
                            },
                            {
                                "match_all": {}
                            },
                            {
                                "bool": {
                                    "minimum_should_match": 1,
                                    "should": [
                                        {
                                            "match_phrase": {
                                                "00080060 Modality_keyword": "SEG"
                                            }
                                        },
                                        {
                                            "match_phrase": {
                                                "00080060 Modality_keyword": "RTSTRUCT"
                                            }
                                        }
                                    ]
                                }
                            },
                            {
                                "bool": {
                                    "should": [
                                        {
                                            "match_phrase": {
                                                "rtstruct_organ_keyword.keyword": "Lung-Right"
                                            }
                                        },
                                        {
                                            "match_phrase": {
                                                "rtstruct_organ_keyword.keyword": "Lung-Left"
                                            }
                                        }
                                    ],
                                    "minimum_should_match": 1
                                }
                            }
                        ],
                        "filter": [],
                        "should": [],
                        "must_not": []
                    }
                },
                "index": "meta-index"
            }
        }
    ],
    parallel_downloads=5,
    check_modality=False
)

# get_test_images = LocalGetRefSeriesOperator(
#     dag=dag,
#     name="nnunet-cohort",
#     target_level="batch",
#     expected_file_count="all",
#     limit_file_count=5,
#     dicom_tags=[
#         {
#             'id': 'ClinicalTrialProtocolID',
#             'value': 'tcia-lymph'
#         },
#         {
#             'id': 'Modality',
#             'value': 'SEG'
#         },
#     ],
#     modality=None,
#     search_policy=None,
#     parallel_downloads=5,
#     delete_input_on_success=False
# )

sort_gt = LocalSortGtOperator(
    dag=dag,
    batch_name="nnunet-cohort",
    input_operator=get_test_images
)

# dcm2nifti_gt = DcmSeg2ItkOperator(
#     dag=dag,
#     input_operator=get_test_images,
#     batch_name=str(get_test_images.operator_out_dir),
#     seg_filter=organ_filter,
#     parallel_id="gt",
#     output_format='nii.gz',
# )

get_ref_ct_series_from_gt = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_test_images,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
    modality=None,
    batch_name=str(get_test_images.operator_out_dir),
    delete_input_on_success=False

)
dcm2nifti_gt = DcmStruct2Nifti(
    dag=dag,
    input_operator=get_test_images,
    seg_filter=organ_filter,
    dicom_operator=get_ref_ct_series_from_gt,
    batch_name=str(get_test_images.operator_out_dir),
    parallel_id="gt",
    delete_input_on_success=False
)

dcm2nifti_ct = DcmConverterOperator(
    dag=dag,
    input_operator=get_ref_ct_series_from_gt,
    parallel_id="ct",
    parallel_processes=parallel_processes,
    batch_name=str(get_test_images.operator_out_dir),
    output_format='nii.gz'
)

get_input = LocalGetInputDataOperator(
    dag=dag,
    check_modality=True,
    parallel_downloads=5
)

dcm2bin = Bin2DcmOperator(
    dag=dag,
    input_operator=get_input,
    name="extract-binary",
    file_extensions="*.dcm"
)

extract_model = GetTaskModelOperator(
    dag=dag,
    name="unzip-models",
    target_level="batch_element",
    input_operator=dcm2bin,
    operator_out_dir="model-exports",
    mode="install_zip"
)

nnunet_predict = NnUnetOperator(
    dag=dag,
    mode="inference",
    input_modality_operators=[dcm2nifti_ct],
    inf_softmax=True,
    inf_batch_dataset=True,
    inf_threads_prep=1,
    inf_threads_nifti=1,
    inf_remove_if_empty=False,
    interpolation_order=default_interpolation_order,
    models_dir=extract_model.operator_out_dir,
)

do_inference = LocalDataorganizerOperator(
    dag=dag,
    input_operator=nnunet_predict,
    mode="batchelement2batchelement",
    target_batchname=str(get_test_images.operator_out_dir),
    parallel_id="inference",
)

seg_check_inference = SegCheckOperator(
    dag=dag,
    input_operator=do_inference,
    original_img_operator=dcm2nifti_ct,
    target_dict_operator=None,
    parallel_processes=parallel_processes,
    max_overlap_percentage=100,
    merge_found_niftis=False,
    delete_merged_data=False,
    fail_if_overlap=False,
    fail_if_label_already_present=False,
    fail_if_label_id_not_extractable=False,
    force_same_labels=False,
    batch_name=str(get_test_images.operator_out_dir),
    parallel_id="inference",
)

seg_check_gt = SegCheckOperator(
    dag=dag,
    input_operator=dcm2nifti_gt,
    original_img_operator=dcm2nifti_ct,
    target_dict_operator=seg_check_inference,
    parallel_processes=parallel_processes,
    max_overlap_percentage=100,
    merge_found_niftis=True,
    delete_merged_data=False,
    fail_if_overlap=False,
    fail_if_label_already_present=False,
    fail_if_label_id_not_extractable=False,
    force_same_labels=False,
    # operator_out_dir=dcm2nifti_gt.operator_out_dir,
    batch_name=str(get_test_images.operator_out_dir),
    parallel_id="gt",
)

nnunet_ensemble = NnUnetOperator(
    dag=dag,
    input_operator=nnunet_predict,
    mode="ensemble",
    prep_min_combination=None,
    inf_threads_nifti=1,
)

do_ensemble = LocalDataorganizerOperator(
    dag=dag,
    input_operator=nnunet_ensemble,
    mode="batch2batchelement",
    target_batchname=str(get_test_images.operator_out_dir),
    parallel_id="ensemble",
)

seg_check_ensemble = SegCheckOperator(
    dag=dag,
    input_operator=do_ensemble,
    original_img_operator=dcm2nifti_ct,
    parallel_processes=parallel_processes,
    max_overlap_percentage=100,
    target_dict_operator=seg_check_inference,
    merge_found_niftis=False,
    delete_merged_data=False,
    fail_if_overlap=False,
    fail_if_label_already_present=False,
    fail_if_label_id_not_extractable=False,
    force_same_labels=False,
    batch_name=str(get_test_images.operator_out_dir),
    parallel_id="ensemble",
)

evaluation = DiceEvaluationOperator(
    dag=dag,
    anonymize=True,
    gt_operator=seg_check_gt,
    input_operator=seg_check_inference,
    ensemble_operator=seg_check_ensemble,
    parallel_processes=1,
    parallel_id="",
    trigger_rule="all_done",
    batch_name=str(get_test_images.operator_out_dir)
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=False)

get_test_images >> sort_gt >> get_ref_ct_series_from_gt >> dcm2nifti_ct >> nnunet_predict >> do_inference >> seg_check_inference >> seg_check_gt >> evaluation
get_ref_ct_series_from_gt >> dcm2nifti_gt >> seg_check_gt
get_input >> dcm2bin >> extract_model >> nnunet_predict >> nnunet_ensemble >> do_ensemble
do_inference >> do_ensemble >> seg_check_ensemble >> evaluation
seg_check_inference >> evaluation >> clean
