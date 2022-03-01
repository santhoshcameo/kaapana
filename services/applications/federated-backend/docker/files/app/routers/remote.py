from typing import Optional, List
import requests
from fastapi import APIRouter, UploadFile, Response, File, Header, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db

from app import crud
from app import schemas


router = APIRouter()


@router.get("/minio-presigned-url")
async def get_minio_presigned_url(presigned_url: str = Header(...)):
    print(f'http://minio-service.store.svc:9000{presigned_url}')
    resp = requests.get(f'http://minio-service.store.svc:9000{presigned_url}')
    # excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    # headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    return Response(resp.content, resp.status_code)

@router.post("/minio-presigned-url")
async def post_minio_presigned_url(file: UploadFile = File(...), presigned_url: str = Header(...)):
    resp = requests.put(f'http://minio-service.store.svc:9000{presigned_url}', data=file.file)
    # excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    # headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    # print(resp)
    response = Response(resp.content, resp.status_code)
    return response

@router.get("/job", response_model=schemas.JobWithKaapanaInstance)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    return crud.get_job(db, job_id)

@router.get("/jobs", response_model=List[schemas.JobWithKaapanaInstance])
async def get_jobs(node_id: str = None, status: str = None, db: Session = Depends(get_db)):
    return crud.get_jobs(db, node_id, status, remote=True)

@router.put("/job", response_model=schemas.JobWithKaapanaInstance)
async def put_job(job: schemas.JobUpdate, db: Session = Depends(get_db)):
    return crud.update_job(db, job, remote=True)

@router.delete("/job")
async def delete_job(job_id: int, db: Session = Depends(get_db)):
    return crud.delete_job(db, job_id, remote=True)

@router.put("/remote-kaapana-instance")
async def put_remote_kaapana_instance(remote_kaapana_instance: schemas.RemoteKaapanaInstanceUpdateExternal, db: Session = Depends(get_db)):
    return crud.create_and_update_remote_kaapana_instance(db=db, remote_kaapana_instance=remote_kaapana_instance, action='external_update')