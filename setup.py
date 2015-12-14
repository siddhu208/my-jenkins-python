from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='jenkinssai',
      version='0.1',
      description='Jenkins package',
      long_description=readme(),
      #classifiers=[
      #      'Development Status :: 3 - Alpha',
      #      'License :: OSI NOT Approved :: SELF License',
      #      'Programming Language :: Python :: 2.7',
      #      'Topic :: Text Processing :: Linguistic',
      #],
      #keywords='jenkins',
      url='',
      author='Sai Siddartha Thotapalli',
      author_email='siddhu_to@yahoo.com',
      license='SELF',
      packages=[
            'jenkinssai'
      ],
      install_requires=[
            'httplib2',
            'json',
            'yaml',
            'os'
      ],
      ## dependency_links=['http://github.com/user/repo/tarball/master#egg=package-1.0'], for packages that are not in PYPI.
      include_package_data=True, ## This will include package data i.e., all non-code files.
      zip_safe=False,
      test_suite='nose.collector',
      tests_require=['nose'])