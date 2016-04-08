FROM python:3.5-onbuild
ENTRYPOINT ["python", "ec2_ami_copy.py"]
