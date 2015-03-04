#!/usr/bin/env python


from distutils.core import setup

setup(name='ADSHLI',
      version='0.3.1',
      description='A high level client for the Twincat ADS/AMS protocol',
      author='Simon Waid',
      author_email='simon_waid@gmx.net',
      url='https://github.com/simonwaid/adshli',
      packages=['adshli'],
      license="LGPL",
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: Python',
          'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
          ],
     )