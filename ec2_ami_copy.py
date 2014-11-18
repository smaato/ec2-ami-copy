#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A script to copy a public AMI to the own AWS account.

Allows to enable enhanced networking while copying and sets more convenient
defaults for the size of the root image and the number of ephemeral volumes.

Author: Daniel Roschka <daniel@smaato.com>
Copyright: Smaato Inc. 2014
URL: https://github.com/smaato/ec2-ami-copy
"""

import argparse
import logging
from time import sleep
import sys
try:
    from boto.ec2 import connect_to_region
    from boto.ec2.blockdevicemapping import BlockDeviceType
    from boto.ec2.blockdevicemapping import BlockDeviceMapping
    from boto.exception import EC2ResponseError
except ImportError:
    print('boto is required for this script. Please install it before proceeding.')
    sys.exit(1)


def copy_snapshot(connection, source_region, snapshot_id):
    """Copies a snapshot. Used to copy the snapshot separately from the AMI."""
    try:
        source_snapshot = connection.get_all_snapshots(snapshot_ids=snapshot_id)[0]
    except EC2ResponseError as exc:
        logging.critical('Getting the snapshot of the source AMI failed: %s', exc.error_message)
        sys.exit(1)

    try:
        target_snapshot_id = connection.copy_snapshot(source_region=source_region,
                                 source_snapshot_id=source_snapshot.id,
                                 description=source_snapshot.description)
    except EC2ResponseError as exc:
        logging.critical('Copying the snapshot of the source AMI failed: %s', exc.error_message)
        sys.exit(1)

    # wait until copying the snapshot has been finished
    while connection.get_all_snapshots(snapshot_ids=target_snapshot_id)[0].status == 'pending':
        logging.debug('Waiting for completion of the snapshot copy.')
        sleep(5)

    if connection.get_all_snapshots(snapshot_ids=target_snapshot_id)[0].status == 'error':
        logging.critical('Copying the snapshot of the source AMI failed: The new snapshot ' +
                         '(%s) is broken.', target_snapshot_id)
        sys.exit(1)

    return target_snapshot_id


def build_block_device_map(source_image, target_snapshot_id):
    """Creates a block device map which is used for the copied AMI.

    The created block device map contains a root volumes with 10GB of storage
    on general purpose SSD (gp2) as well as up to four ephemeral volumes.
    Storage volume as well as number of ephemeral volumes can be changed when
    launching an instance out of the resulting AMI.
    """
    root_device_name = source_image.root_device_name

    del_root_volume = source_image.block_device_mapping[root_device_name].delete_on_termination

    block_device_map = BlockDeviceMapping()
    block_device_map[root_device_name] = BlockDeviceType(snapshot_id=target_snapshot_id,
                                                         size=10,
                                                         volume_type='gp2',
                                                         delete_on_termination=del_root_volume)

    for i in range(0, 4):
        device_name = '/dev/sd%s' % chr(98+i)
        block_device_map[device_name] = BlockDeviceType(ephemeral_name='ephemeral%i' % i)

    return block_device_map


def create_image(connection, source_image, block_device_map, sriov_net_support):
    """Creates a new AMI out of the copied snapshot and the pre-defined block device map."""
    try:
        target_image_id = connection.register_image(name=source_image.name,
                              architecture=source_image.architecture,
                              kernel_id=source_image.kernel_id,
                              ramdisk_id=source_image.ramdisk_id,
                              root_device_name=source_image.root_device_name,
                              block_device_map=block_device_map,
                              virtualization_type=source_image.virtualization_type,
                              sriov_net_support=sriov_net_support)
    except EC2ResponseError as exc:
        logging.critical('The creation of the copied AMI failed: %s', exc.error_message)
        sys.exit(1)

    while connection.get_all_images(image_ids=target_image_id)[0].state == 'pending':
        logging.debug('Waiting for completion of the AMI creation.')
        sleep(5)

    if connection.get_all_images(image_ids=target_image_id)[0].state == 'failed':
        logging.critical('The creation of the copied AMI failed. The new AMI (%s) is broken.',
                         target_image_id)
        sys.exit(1)

    return target_image_id


def main():
    """Main method used to setup basic stuff and runs all other methods.

    This method initalizes logging, parsing of command line arguments and
    orchestrating the copy of the AMI.
    """
    parser = argparse.ArgumentParser(description='Script to copy public AMIs to the own account.')
    parser.add_argument('-a', '--aws-access-key', dest='aws_access_key', required=True)
    parser.add_argument('-s', '--aws-secret-key', dest='aws_secret_key', required=True)
    parser.add_argument('-r', '--region', dest='region', default='us-east-1',
                        help='The AWS region which contains the source AMI and will contain the ' +
                        'target AMI as well.')
    parser.add_argument('-i', '--ami-id', dest='ami_id', required=True,
                        help='The ID of the AMI to copy.')
    parser.add_argument('-l', '--log-level', dest='log_level', default='INFO',
                        help='Sets the log level of the script. Default is INFO.')
    parser.add_argument('-e', '--enhanced-networking', dest='sriov_net_support',
                        action='store_true', default=False,
                        help='Specify if you want to have enhanced networking enabled in the ' +
                        'resulting image.')
    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)s %(levelname)s: ' \
                                       '%(message)s', level=args.log_level)
    logging.getLogger('boto').setLevel(logging.CRITICAL)

    connection = connect_to_region(args.region,
                                   aws_access_key_id=args.aws_access_key,
                                   aws_secret_access_key=args.aws_secret_key)

    # get information about the image which should be copied
    try:
        source_image = connection.get_all_images(image_ids=args.ami_id)[0]
    except EC2ResponseError as exc:
        logging.critical('Getting the source AMI failed: %s', exc.error_message)
        sys.exit(1)

    # copy the snapshot representing the root file system of the AMI
    root_device_name = source_image.root_device_name
    source_snapshot_id = source_image.block_device_mapping[root_device_name].snapshot_id
    target_snapshot_id = copy_snapshot(connection, args.region, source_snapshot_id)

    # overwrite the option for enhanced networking if necessary
    if args.sriov_net_support:
        sriov_net_support = 'simple'
    else:
        sriov_net_support = source_image.sriov_net_support

    block_device_map = build_block_device_map(source_image, target_snapshot_id)

    target_image_id = create_image(connection, source_image, block_device_map, sriov_net_support)

    logging.info('The new image is available as: %s', target_image_id)


if __name__ == '__main__':
    main()
