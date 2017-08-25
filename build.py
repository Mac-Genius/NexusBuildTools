#!/usr/bin/env python

from urllib import request
import json
import re
from os import path
from subprocess import call
try: 
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup

def fetch_versions():
	version_html = request.urlopen('https://hub.spigotmc.org/versions/').read().decode('utf8')
	parsed_html = BeautifulSoup(version_html, 'html.parser')
	a_array = parsed_html.body.find_all('a')
	versions = list()
	for atag in a_array:
		text = atag.text
		regex = re.search('([0-9]+\.){1,2}([0-9]+)', text)
		if regex:
			final = regex.group(0)
			versions.append(final)
	return versions

def fetch_version_info(versions):
	version_dict = dict()
	for version in versions:
		version_data = request.urlopen('https://hub.spigotmc.org/versions/' + version + '.json').read().decode('utf8')
		version_dict[version] = json.loads(version_data)
	return version_dict

def load_prev_version_info():
	if (path.exists('build_data_nexus.json')):
		version_file = open('build_data_nexus.json', 'r')
		info = version_file.read()
		version_file.close()
		return json.loads(info)
	else:
		info = open('build_data_nexus.json', 'w')
		info.write('{}')
		info.close()
		return dict()

def save_version_info(version_info):
	info = open('build_data_nexus.json', 'w')
	info.write(json.dumps(version_info, indent=4, sort_keys=True))
	info.close()

def get_needed_updates(old_data, new_data, config):
	to_update = list()
	for version in new_data:
		if version not in config['ignored_versions']:
			update = False
			if version in old_data:
				if new_data[version]['refs']['Bukkit'] != old_data[version]['refs']['Bukkit']:
					to_update.append(version)
					update = True
				if new_data[version]['refs']['CraftBukkit'] != old_data[version]['refs']['CraftBukkit']:
					to_update.append(version)
					update = True
				if new_data[version]['refs']['Spigot'] != old_data[version]['refs']['Spigot']:
					to_update.append(version)
					update = True
			else:
				to_update.append(version)
				update = True
			if update:
				print('Version', version, 'will be updated.')
			else:
				print('Version', version, 'is up to date.')
	return to_update

def run_build_tools(version_array, config):
	success_array = list()
	for version in version_array:
		print('Building version:', version)
		code = call(['java', '-jar', 'BuildTools.jar', '--rev', version])
		if code == 0:
			nexus_delete_code = call(['curl', '-L', '-X', 'DELETE', '-u', config['username'] + ':' + config['password'], config['nexus_url'] + '/service/local/repositories/releases/content/org/spigotmc/spigot/' + version])
			if nexus_delete_code == 0:
				nexus_add_code = call(['apache-maven-3.5.0/bin/mvn', 'deploy:deploy-file', '-DgroupId=org.spigotmc', '-DartifactId=spigot', '-Dversion=' + version, '-Dpackaging=jar', '-Dfile=spigot-' + version + '.jar', '-DrepositoryId=nexus', '-Durl=' + config['nexus_url'] + '/content/repositories/releases/'])
				if nexus_add_code == 0:
					success_array.append(version)
				else:
					print('Failed to upload version', version, 'of Spigot to Nexus.')
			else:
				print('Failed to delete version ' + version + ' of Spigot from Nexus.')
		else:
			print('Failed to build version', version, 'of Spigot.')
	return success_array

def fetch_config():
	if (path.exists('config.json')):
		config = open('config.json', 'r')
		config_dict = json.loads(config.read())
		config.close()
		return config_dict
	else:
		temp_dict = dict()
		temp_dict['username'] = ''
		temp_dict['password'] = ''
		temp_dict['nexus_url'] = ''
		temp_dict['ignored_versions'] = list()
		config = open('config.json', 'w')
		config.write(json.dumps(temp_dict, indent=4, sort_keys=True))
		config.close()
		return temp_dict

def main():
	config = fetch_config()
	new_version_data = fetch_version_info(fetch_versions())
	old_version_data = load_prev_version_info()
	version_array = get_needed_updates(old_version_data, new_version_data, config)
	successful_versions = run_build_tools(version_array, config)

	for version in successful_versions:
		old_version_data[version] = new_version_data[version]
	save_version_info(old_version_data)

if __name__ == '__main__':
	main()
