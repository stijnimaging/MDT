#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
import argparse
import glob
import os

import numpy as np

import mdt
from argcomplete.completers import FilesCompleter
import textwrap

from mdt.shell_utils import BasicShellApplication
from mdt.utils import split_image_path

__author__ = 'Robbert Harms'
__date__ = "2015-08-18"
__maintainer__ = "Robbert Harms"
__email__ = "robbert.harms@maastrichtuniversity.nl"


class MathImg(BasicShellApplication):

    def _get_arg_parser(self):
        description = textwrap.dedent("""
            Evaluate an expression on a set of images.

            This is meant to quickly convert/combine one or two maps with a mathematical expression. The expression
            can be any valid python string.

            The input list of images are loaded as numpy arrays and stored in the array 'input', or equivalent, 'i'.
            Next, the expression is evaluated using the input images and the result is stored in the indicated file.

            In the expression you can either use the arrays 'input', 'i' with linear indices to your input images,
            or/and you can use alphabetic characters for each image. For example, if you have specified 2 input images
            you can address them as:
                input[0] or i[0] or a
                input[1] or i[1] or b

            You can use every single alphabetic character except for the i since that one is reserved for the array.

            The module numpy is also available using the variable 'np'. This allows expressions like:
                np.mean(np.concatenate(i, axis=3), axis=3)
            to get the mean value per voxel of all the input images.
        """)
        description += self._get_citation_message()

        epilog = textwrap.dedent("""
            Examples of use:
                mdt-math-img fiso.nii ficvf.nii '(1-input[0]) * i[1]' Wic.w.nii.gz
                mdt-math-img fiso.nii ficvf.nii '(1-a) * b' Wic.w.nii.gz
                mdt-math-img *.nii.gz 'np.mean(np.concatenate(i, axis=3), axis=3)' output.nii.gz
        """)

        parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                         formatter_class=argparse.RawTextHelpFormatter)

        parser.add_argument('input_files', metavar='input_files', nargs="+", type=str,
                            help="The input images to use")

        parser.add_argument('expr', metavar='expr', type=str,
                            help="The expression to evaluate.")

        parser.add_argument('output_file',
                            action=mdt.shell_utils.get_argparse_extension_checker(['.nii', '.nii.gz', '.hdr', '.img']),
                            help='the base output name').completer = \
            FilesCompleter(['nii', 'gz', 'hdr', 'img'], directories=False)

        parser.add_argument('--verbose', '-v', action='store_true', help="Verbose, prints runtime information")

        return parser

    def run(self, args):
        output_file = os.path.realpath(args.output_file)

        if os.path.isfile(output_file):
            os.remove(output_file)

        file_names = []
        for file in args.input_files:
            file_names.extend(glob.glob(file))

        if args.verbose:
            print('')

        images = [mdt.load_data_volume(dwi_image) for dwi_image in file_names]
        context_dict = {'input': images, 'i': images}
        alpha_chars = list('abcdefghjklmnopqrstuvwxyz')

        for ind, image in enumerate(images):
            context_dict.update({alpha_chars[ind]: image})

            if args.verbose:
                print('Input {ind} ({alpha}):'.format(ind=ind, alpha=alpha_chars[ind]))
                print('    name: {}'.format(split_image_path(file_names[ind])[1]))
                print('    shape: {}'.format(str(image.shape)))

        if args.verbose:
            print('')
            print("Evaluating: '{expr}'".format(expr=args.expr))

        output = eval(args.expr, {'np': np}, context_dict)

        if len(output.shape) == 3:
            if args.verbose:
                print('')
                print('Output is 3d, reshaping to 4d')
                print('Final output shape: {shape}'.format(shape=str(output.shape)))
            output = output[..., np.newaxis]
        else:
            if args.verbose:
                print('')
                print('Output shape: {shape}'.format(shape=str(output.shape)))

        if args.verbose:
            print('')

        mdt.write_image(output_file, output, mdt.load_nifti(file_names[0]).get_header())


if __name__ == '__main__':
    MathImg().start()