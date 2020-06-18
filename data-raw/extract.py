import pandas
import subprocess
import os

# Selected ecosystem names (see libraries.io)
ECOSYSTEMS = ['Cargo', 'Packagist', 'NPM', 'Rubygems']
# Version of the libraries.io dataset
LIBRARIESIO_VERSION = '1.6.0-2020-01-12'
# Location of the libraries.io dataset
PATH_TO_LIBRARIESIO = '/data/libio1.6/'

# Fields to keep for "version-[...].csv"
VERSION_FIELDS = {
    'Platform': 'platform',
    'Project Name': 'package',
    'Number': 'version',
    'Published Timestamp': 'date',
}
# Fields to keep for "dependencies-[...].csv"
DEPENDENCY_FIELDS = {
    'Platform': 'platform',
    'Project Name': 'source',
    'Version Number': 'version',
    'Dependency Name': 'target',
    'Dependency Kind': 'kind',
    'Dependency Requirements': 'constraint',
    'Dependency Platform': 'target_platform'
}
# Fields to keep for "projects_with_repository_fields-[...].csv"
REPOSITORY_FIELDS = {
    'Platform': 'platform',
    'Name': 'package',
    'Repository Host Type': 'host',
    'Repository URL': 'repository',
    'Repository Created Timestamp': 'date',
    'Dependent Projects Count': 'dependent_packages',
    'Dependent Repositories Count': 'dependent_projects',
    'Repository Stars Count': 'stars',
    'Repository Forks Count': 'forks',
    'Repository Watchers Count': 'watchers',
    'Repository Open Issues Count': 'issues',
    'Repository Contributors Count': 'contributors',
    'Repository Size': 'size',
}
# Kind of dependencies to keep 
DEPENDENCY_KEPT_KINDS = {
    'Cargo': ['normal', 'runtime'],
    'Packagist': ['runtime'],
    'NPM': ['runtime'],
    'Rubygems': ['runtime'],
}
# Optimization purposes:
DATA_TYPES = {
    'platform': 'category',
    'kind': 'category',
    'target': 'category',
    'constraint': 'category',
    'host': 'category',
}

if __name__ == '__main__':
    for ecosystem in ECOSYSTEMS:
        if os.path.isfile('{}-releases.csv.gz'.format(ecosystem)) and os.path.isfile('{}-dependencies.csv.gz'.format(ecosystem)) and os.path.isfile('{}-repositories.csv.gz'.format(ecosystem)):
            print('Skipping {}'.format(ecosystem))
            continue
            
        print('Extracting data for {}, this could take some time...'.format(ecosystem))
        with open('temp-releases.csv', 'w') as out:
            filename = os.path.join(PATH_TO_LIBRARIESIO, 'versions-{}.csv'.format(LIBRARIESIO_VERSION))
            subprocess.call(['head', '-1', filename], stdout=out)
            subprocess.call(['grep', ',{},'.format(ecosystem), filename], stdout=out)

        with open('temp-dependencies.csv', 'w') as out:
            filename = os.path.join(PATH_TO_LIBRARIESIO, 'dependencies-{}.csv'.format(LIBRARIESIO_VERSION))
            subprocess.call(['head', '-1', filename], stdout=out)
            subprocess.call(['grep', ',{},'.format(ecosystem), filename], stdout=out)    

        with open('temp-repositories.csv', 'w') as out:
            filename = os.path.join(PATH_TO_LIBRARIESIO, 'projects_with_repository_fields-{}.csv'.format(LIBRARIESIO_VERSION))
            subprocess.call(['head', '-1', filename], stdout=out)
            subprocess.call(['grep', ',{},'.format(ecosystem), filename], stdout=out)    
            
        print('Loading data in memory')
        df_releases = pandas.read_csv(
            'temp-releases.csv',
            index_col=False,
            engine='c',
            usecols=list(VERSION_FIELDS.keys()),
            dtype={k: DATA_TYPES.get(v, 'object') for k, v in VERSION_FIELDS.items()},
        ).rename(columns=VERSION_FIELDS).query('platform == "{}"'.format(ecosystem))

        df_deps = pandas.read_csv(
            'temp-dependencies.csv',
            index_col=False,
            engine='c',
            usecols=list(DEPENDENCY_FIELDS.keys()),
            dtype={k: DATA_TYPES.get(v, 'object') for k, v in DEPENDENCY_FIELDS.items()},
        ).rename(columns=DEPENDENCY_FIELDS).query('platform == "{0}" and target_platform == "{0}"'.format(ecosystem))
        print('.. {} versions and {} dependencies loaded'.format(len(df_releases), len(df_deps)))

        print('Filtering dependencies based on "kind"')
        df_deps = df_deps.query(' or '.join(['kind == "{}"'.format(kind) for kind in DEPENDENCY_KEPT_KINDS[ecosystem]]))
        print('.. {} remaining dependencies'.format(len(df_deps)))

        print('Removing unknown packages')
        packages = df_releases['package'].drop_duplicates()
        print('.. {} known packages'.format(len(packages)))
        df_deps = df_deps.merge(
            df_releases[['package', 'version']],
            how='inner',
            left_on=['source', 'version'],
            right_on=['package', 'version'],
        ).drop(columns=['package'])
        df_deps = df_deps[df_deps['target'].isin(packages)]
        print('.. {} remaining dependencies'.format(len(df_deps)))

        print('Loading projects with repository')
        df_repo = pandas.read_csv(
            'temp-repositories.csv',
            index_col=False,
            engine='c',
            usecols=list(REPOSITORY_FIELDS.keys()),
            dtype={k: DATA_TYPES.get(v, 'object') for k, v in REPOSITORY_FIELDS.items()},
        ).rename(columns=REPOSITORY_FIELDS).query('platform == "{0}" and host == "{1}"'.format(ecosystem, 'GitHub'))
        print('.. {} repositories'.format(len(df_repo)))
        
        print('Removing unknown packages')
        df_repo = df_repo[df_repo['package'].isin(packages)]
        print('.. {} remaining repositories'.format(len(df_repo)))
        
        print('Exporting to compressed csv')
        df_releases[['package', 'version', 'date']].to_csv(
            '{}-releases.csv.gz'.format(ecosystem),
            index=False,
            compression='gzip',
        )

        df_deps[['source', 'version', 'target', 'constraint']].to_csv(
            '{}-dependencies.csv.gz'.format(ecosystem),
            index=False,
            compression='gzip',
        )
        
        df_repo[['package', 'repository', 'date', 'dependent_projects', 'stars', 'forks', 'watchers', 'issues', 'contributors', 'size']].to_csv(
            '{}-repositories.csv.gz'.format(ecosystem),
            index=False,
            compression='gzip',
        )
        
        print('Deleting temporary files')
        subprocess.call(['rm', 'temp-releases.csv'])
        subprocess.call(['rm', 'temp-dependencies.csv'])
        subprocess.call(['rm', 'temp-repositories.csv'])
        print()
        