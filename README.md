# Overview

This repository contains a python script which provides the ability to copy
a public AWS AMI to the own AWS account. Such a script is necessary, because
AWS currently doesn't allow to copy public AMIs, but only AMIs you already own.

So this script circumvents that AWS-made limitation by copying the snapshot
of the root filesystem of the public AMI and creating a AMI with that snapshot
as root filesystem, by keeping the remaining properties of the original AMI.

It doesn't keep all properties of the original AMI, so the root filesystem size
is set to 10GB by default (if it's been lower than that) and the number of
attached ephemeral volumes is set to four (which is usually more than the
original AMI had). Both of these properties can be changed of course when
creating an instance out of the AMI.

The script also allows to enable enhanced networking on the produced AMI. But
keep in mind that this only works when the operating system of the original AMI
already supports enhanced networking and you intend to start the AMI in VPC
only.

# Usage

* The only requirements beside python itself to get the script running are boto
  (https://github.com/boto/boto/) and valid AWS credentials.
* To call the script simply do:
```
foo@bar:~$ ./ec2_ami_copy.py -a $access-key -s $secret-key -i $ami-id
```
* Calling the script with ```--help``` will show you all available options:
```
foo@bar:~$ ./ec2_ami_copy.py --help
usage: ec2_ami_copy.py [-h] -a AWS_ACCESS_KEY -s AWS_SECRET_KEY [-r REGION] -i
                       AMI_ID [-l LOG_LEVEL] [-e] [-S ROOT_VOLUME_SIZE]

Script to copy public AMIs to the own account.

optional arguments:
  -h, --help            show this help message and exit
  -a AWS_ACCESS_KEY, --aws-access-key AWS_ACCESS_KEY
  -s AWS_SECRET_KEY, --aws-secret-key AWS_SECRET_KEY
  -r REGION, --region REGION
                        The AWS region which contains the source AMI and will
                        contain the target AMI as well.
  -i AMI_ID, --ami-id AMI_ID
                        The ID of the AMI to copy.
  -l LOG_LEVEL, --log-level LOG_LEVEL
                        Sets the log level of the script. Defaults to INFO.
  -e, --enhanced-networking
                        Specify if you want to enforce enabled enhanced
                        networking in the resulting image. If not set the
                        setting for enhanced networking willbe taken from the
                        original AMI.
  -S ROOT_VOLUME_SIZE, --root-volume-size ROOT_VOLUME_SIZE
                        The minimum size in GB the root volume should have in
                        the resulting AMI. Defaults to 10.
```

# Docker

If your environment doesn't contain Python (or not ideal for it), you can run the above ec2_ami_copy via Docker:

```
docker build -t ec2-ami-copy .
docker run -it --rm --name ec2-ami-copy ec2 -ami-copy python ec2_ami_copy.py -a $access-key -s $secret-key -i $ami-id
```

# Contribution

Pull Requests are welcome!
