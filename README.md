# ExploreDocker
This project hopes to explore docker containers from the security perspective in order to determine leftover Common Vulnerabilities and Exposures (CVEs) inside containers. Additionally, the main purpose is to compare similar conatiners' contents in the form of software packages. This comparison is intended to culminate in the determining of which docker container has fewer CVEs.

## Use

The main use is inside the python file called `analyze_docker.py`. Using this file, a `DockerExplorer` object is created to compare given sets of similar docker containers. These sets are typically created through scraping docker hub for similarly purposed containers. An example is below,
```
from analyze_docker import DockerExplorer
DockerExplorer explorer = DockerExplorer(1)
# add set of docker containers to explore (they are explored in this call)
explorer.add_set('webservers', ['hirlanda/webserver', 'acidozik/nodejswebserver'], save_dir='./save_dir')
# compare a set of docker containers
exporer.compare_set('webservers', './save_dir')
# print closeness metric
print(explorer.closeness('webservers', 'hirlanda/webserver', 'acidozik/nodejswebserver', './save_dir'))
```

## Authors

* **Rajiv Sarvepalli** - *Created* - [rajivsarvepalli](https://github.com/rajivsarvepalli)
