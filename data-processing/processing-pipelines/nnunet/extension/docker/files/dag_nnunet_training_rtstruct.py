import random
from datetime import datetime, timedelta

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSeg2ItkOperator import DcmSeg2ItkOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from kaapana.operators.Pdf2DcmOperator import Pdf2DcmOperator
from kaapana.operators.ZipUnzipOperator import ZipUnzipOperator
from kaapana.operators.DcmStruct2Nifti import DcmStruct2Nifti
from airflow.api.common.experimental import pool as pool_api
from airflow.utils.log.logging_mixin import LoggingMixin
from nnunet.NnUnetOperator import NnUnetOperator
from nnunet.SegCheckOperator import SegCheckOperator
from airflow.utils.dates import days_ago
from airflow.models import DAG
from kaapana.blueprints.kaapana_global_variables import INSTANCE_NAME, SERVICES_NAMESPACE


study_id = "Kaapana"
# TASK_NAME = f"Task{random.randint(100,999):03}_{INSTANCE_NAME}_train"
TASK_NAME = f"Task{random.randint(100,999):03}_RACOON_{INSTANCE_NAME}_{datetime.now().strftime('%d%m%y-%H%M')}"
seg_filter = ""
prep_modalities = "CT"
default_model = "3d_lowres"
train_network_trainer = "nnUNetTrainerV2"
ae_title = "nnUnet-results"
max_epochs = 1000
dicom_model_slice_size_limit = 70
training_results_study_uid = None
gpu_count_pool = pool_api.get_pool(name="NODE_GPU_COUNT")
gpu_count = int(gpu_count_pool.slots) if gpu_count_pool is not None and gpu_count_pool != 0 else 1
max_active_runs = gpu_count + 1
concurrency = max_active_runs * 2
prep_threads = 2

ui_forms = {
    "publication_form": {
        "type": "object",
        "properties": {
            "title": {
                "title": "Title",
                "default": "Automated Design of Deep Learning Methods\n for Biomedical Image Segmentation",
                "type": "string",
                "readOnly": True,
            },
            "authors": {
                "title": "Authors",
                "default": "Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein",
                "type": "string",
                "readOnly": True,
            },
            "link": {
                "title": "DOI",
                "default": "https://arxiv.org/abs/1904.08128",
                "description": "DOI",
                "type": "string",
                "readOnly": True,
            },
            "confirmation": {
                "title": "Accept",
                "default": False,
                "type": "boolean",
                "readOnly": True,
                "required": True,
            }
        }
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "task": {
                "title": "TASK_NAME",
                "description": "Specify a name for the training task",
                "type": "string",
                "default": TASK_NAME,
                "required": True
            },
            "model": {
                "title": "Network",
                "default": default_model,
                "description": "2d, 3d_lowres, 3d_fullres or 3d_cascade_fullres",
                "enum": ["2d", "3d_lowres", "3d_fullres", "3d_cascade_fullres"],
                "type": "string",
                "readOnly": False,
                "required": True
            },
            "train_network_trainer": {
                "title": "Network-trainer",
                "default": train_network_trainer,
                "description": "nnUNetTrainerV2 or nnUNetTrainerV2CascadeFullRes",
                "type": "string",
                "readOnly": False,
            },
            "prep_modalities": {
                "title": "Modalities",
                "default": prep_modalities,
                "description": "eg 'CT' or 'CT,PET' etc.",
                "type": "string",
                "readOnly": False,
            },
            "seg_filter": {
                "title": "Seg",
                "default": seg_filter,
                "description": "Select organ for multi-label DICOM SEGs: eg 'liver' or 'spleen,liver'",
                "type": "string",
                "readOnly": False,
            },
            "instance_name": {
                "title": "Instance name",
                "description": "Specify an ID for the node / site",
                "type": "string",
                "default": INSTANCE_NAME,
                "required": True
            },
            "shuffle_seed": {
                "title": "Shuffle seed",
                "default": 0,
                "description": "Set a seed.",
                "type": "integer",
                "readOnly": False,
            },
            "test_percentage": {
                "title": "Test percentage",
                "default": 0,
                "description": "Set % of data for the test-set.",
                "type": "integer",
                "readOnly": False,
            },
            "training_description": {
                "title": "Training description",
                "default": "nnUnet Segmentation",
                "description": "Specify a version.",
                "type": "string",
                "readOnly": False,
            },
            "body_part": {
                "title": "Body Part",
                "description": "Body part, which needs to be present in the image.",
                "default": "N/A",
                "type": "string",
                "readOnly": False,
            },
            "train_max_epochs": {
                "title": "Epochs",
                "default": max_epochs,
                "description": "Specify max epochs.",
                "type": "integer",
                "required": True,
                "readOnly": False
            },
            # "version": {
            #     "title": "Version",
            #     "default": "0.0.1-alpha",
            #     "description": "Specify a version.",
            #     "type": "string",
            #     "readOnly": False,
            # },
            # "training_reference": {
            #     "title": "Training reference",
            #     "default": "nnUNet",
            #     "description": "Set a reference.",
            #     "type": "string",
            #     "readOnly": False,
            # },
            "input": {
                "title": "Input Modality",
                "default": "SEG",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
            },
        }
    }
}
args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 1,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='nnunet-training-rtstruct',
    default_args=args,
    concurrency=concurrency,
    max_active_runs=max_active_runs,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(
    dag=dag,
    check_modality=False,
    parallel_downloads=5,
    delete_input_on_success=False
)

get_ref_ct_series_from_struct = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_input,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
    modality=None,
    delete_input_on_success=False
)

dcmstruct2nifti = DcmStruct2Nifti(
    dag=dag,
    input_operator=get_input,
    dicom_operator=get_ref_ct_series_from_struct,
    delete_input_on_success=False
)

# dcm2nifti_seg = DcmSeg2ItkOperator(
#     dag=dag,
#     input_operator=get_input,
#     output_format="nii.gz",
#     seg_filter=seg_filter,
#     parallel_id='seg',
#     delete_input_on_success=True
# )


dcm2nifti_ct = DcmConverterOperator(
    dag=dag,
    input_operator=get_ref_ct_series_from_struct,
    output_format='nii.gz',
    delete_input_on_success=False
)

check_seg = SegCheckOperator(
    dag=dag,
    input_operator=dcmstruct2nifti,
    original_img_operator=dcm2nifti_ct,
    parallel_processes=3,
    delete_merged_data=True,
    fail_if_overlap=False,
    fail_if_label_already_present=False,
    fail_if_label_id_not_extractable=False,
    force_same_labels=False,
)

nnunet_preprocess = NnUnetOperator(
    dag=dag,
    mode="preprocess",
    input_modality_operators=[dcm2nifti_ct],
    prep_label_operators=[check_seg],
    prep_use_nifti_labels=False,
    prep_modalities=prep_modalities.split(","),
    prep_processes_low=prep_threads+1,
    prep_processes_full=prep_threads,
    prep_preprocess=True,
    prep_check_integrity=True,
    prep_copy_data=True,
    prep_exit_on_issue=True,
    retries=0,
    instance_name=INSTANCE_NAME,
    delete_input_on_success=True
)

nnunet_train = NnUnetOperator(
    dag=dag,
    mode="training",
    train_max_epochs=max_epochs,
    input_operator=nnunet_preprocess,
    model=default_model,
    train_network_trainer=train_network_trainer,
    train_fold='all',
    retries=0,
    delete_input_on_success=True
)

pdf2dcm = Pdf2DcmOperator(
    dag=dag,
    input_operator=nnunet_train,
    study_uid=training_results_study_uid,
    aetitle=ae_title,
    pdf_title=f"Training Report nnUNet {TASK_NAME} {datetime.now().strftime('%d.%m.%Y %H:%M')}",
    delete_input_on_success=False
)

dcmseg_send_pdf = DcmSendOperator(
    dag=dag,
    parallel_id="pdf",
    level="batch",
    pacs_host=f'ctp-dicom-service.{SERVICES_NAMESPACE}.svc',
    pacs_port='11112',
    ae_title=ae_title,
    input_operator=pdf2dcm,
    delete_input_on_success=True
)
zip_model = ZipUnzipOperator(
    dag=dag,
    target_filename=f"nnunet_model.zip",
    whitelist_files="model_latest.model.pkl,model_latest.model,model_final_checkpoint.model,model_final_checkpoint.model.pkl,dataset.json,plans.pkl,*.json,*.png,*.pdf",
    subdir="results/nnUNet",
    mode="zip",
    info_files="dataset.json",
    batch_level=True,
    input_operator=nnunet_train,
    delete_input_on_success=False
)

bin2dcm = Bin2DcmOperator(
    dag=dag,
    name="model2dicom",
    patient_name="nnUNet-model",
    patient_id=INSTANCE_NAME,
    instance_name=INSTANCE_NAME,
    manufacturer="Kaapana",
    manufacturer_model="nnUNet",
    version=nnunet_train.image.split(":")[-1],
    study_id=study_id,
    study_uid=training_results_study_uid,
    protocol_name=None,
    study_description=None,
    series_description=f"nnUNet model {datetime.now().strftime('%d.%m.%Y %H:%M')}",
    size_limit=dicom_model_slice_size_limit,
    input_operator=zip_model,
    file_extensions="*.zip",
    delete_input_on_success=True
)

dcm_send_int = DcmSendOperator(
    dag=dag,
    level="batch",
    pacs_host=f'ctp-dicom-service.{SERVICES_NAMESPACE}.svc',
    pacs_port='11112',
    ae_title=ae_title,
    input_operator=bin2dcm,
    delete_input_on_success=True
)

# dcm_send_ext = DcmSendOperator(
#     dag=dag,
#     level="batch",
#     pacs_host='192.168.0.2',
#     pacs_port='2021',
#     ae_title=ae_title,
#     input_operator=bin2dcm,
#     delete_input_on_success=True
# )

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=False)
get_input >> get_ref_ct_series_from_struct >> dcm2nifti_ct >> check_seg >> nnunet_preprocess >> nnunet_train
get_ref_ct_series_from_struct >> dcmstruct2nifti >> check_seg

nnunet_train >> pdf2dcm >> dcmseg_send_pdf >> clean
nnunet_train >> zip_model >> bin2dcm >> dcm_send_int >> clean
# bin2dcm >> dcm_send_ext