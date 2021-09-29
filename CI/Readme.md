# Continuous integration (CI)

## CI Dashboard

- Go to [ReportPortal](http://10.128.130.252/ui/#kaapana/launches/all)
- User: kaapana
- Password: q1w2e3r4
- -> Launches

## Init new CI server
To start a new instance of the CI server:
`ansible-playbook kaapana/CI/ansible_playbooks/setup_ci_server_playbook.yaml`

- This will start a new OpenStack instance with all CI configuration
- ReportPortal available at http://instance-ip/ui -> default username/pw: default:1q2w3e and superadmin:erebus
- You need to configure a "kaapana" project in report portal + new user
- Adapt the access-token in `kaapana/CI/scripts/start_ci_pipeline.py` to the new user
- Cronjob will trigger the pipeline each night at 12 am
- Http CI trigger running @ http://instance-ip:8080/cikaapana/<branch> 
  - eg: /cikaapana/feature/test or /cikaapana/develop

## CI pipline (cronjob)

### Delete Docker cache from instance @ 12am

- [x] docker system prune -f -a --volumes

### Start main pipeline @ 2am

- [x] Checkout kaapana develop branch & pull
- [x] Trigger CI service via HTTP which then starts CI/scripts/start_ci_pipeline.py

### Quick checks

- [x] Get all Helm Charts
- [X] Extract chart infos   
- [x] Resolve all requirements
- [x] Get all Dockerfiles
- [X] Extract container infos   
- [x] Check base images 
- [x] Check if tag already used
- [x] Compare used containers (charts + operators) to the containers defined in Dockerfiles 

### Helm Charts

- [x] Get all dependencies
- [x] Lint each chart
- [x] Build each chart
- [x] Push each chart

### Docker Containers

- [ ] Hadolint each Dockerfile
- [x] Build each container
- [x] Push each container

## Start fresh CentOS (v. 7 & 8) & Ubuntu instances

- [x] Delete existing OpenStack instances if found
- [x] Start new CentOS (7 & 8) and Ubuntu OpenStack instances

## Kaapana platform deployment and tests

- [x] Install all platform dependencies using latest server install script
- [x] Deploy platform using latest platform install script
- [x] Check if all pods are running
- [x] Basic UI testing (Login, PACS, Flow, etc. available)
- [ ] Delete Openstack Instance
  
## Logs and Email Reports
- [x] Report logs to the CI dashboard (ReportPortal)
- [x] Report issues via email to developers
- [x] Save latest system log to log file

## More testing

- [ ] Send example image
- [ ] Check if metadata available
- [ ] Start segmentation 
- [ ] Check airflow if success
- [ ] Check if results present: DCM SEG, metadata
- [ ] ...

## MORE

1) Linting Helm, YAML, Docker, Shell, Python?, JSON?, XML?
2) Build and push all Docker containers -> container version = branch
3) Test Docker Containers for basic functionality (dgoss?)
4) Build and push all Helm charts
5) Test server install script on VM
6) Install kaapana chart
7) Some basic curl testing if pages are running
8) Run and check test-jobs within the cluster
    1) Send dcm
    2) Send dcmSeg
    3) Check if metadata is available
    4) Start Radiomics
    5) Start Organseg
    6) ... tbd

## Git-Hooks?

### Client
- linting?

### Server
- trigger Jenkins

## Docker testing with dgoss
**Docs**: [Dgoss docs](https://github.com/aelsabbahy/goss/tree/master/extras/dgoss)

## Code quality
### YAML linter
**Docs**: [Yamllint docs](https://yamllint.readthedocs.io/en/stable/quickstart.html)

**installation**:
    pip install --user yamllint

### Docker linter
**Docs**: [Hadolint docs](https://github.com/hadolint/hadolint/releases/)

**installation**:
    wget https://github.com/hadolint/hadolint/releases/download/v1.17.1/hadolint-Linux-x86_64
    chmod +x hadolint-Linux-x86_64
    mv hadolint-Linux-x86_64 /usr/local/bin/hadolint

### Helm linter
**Docs**: [Helm docs](https://helm.sh/docs/using_helm/#installing-helm)

**installation**:
    wget https://get.helm.sh/helm-v2.14.2-linux-amd64.tar.gz
    tar -zxvf helm-v2.14.2-linux-amd64.tar.gz
    mv linux-amd64/helm /usr/local/bin/helm

### Shell linter
**Docs**: [ShellCheck](https://github.com/koalaman/shellcheck/wiki)

**Installation**:
    yum install ShellCheck
