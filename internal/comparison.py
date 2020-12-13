def compare_similar_images(j_dict1, j_dict2):
    packages1 = j_dict1['user_installed_packages']
    packages2 = j_dict2['user_installed_packages']
    same_packages = list()
    different_packages = list()
    different_versions = list()
    found_package = False
    missing_packages = dict(zip(packages2.keys(), [True]*len(packages2)))
    for p in packages1:
        found_package = False
        if packages1[p] == 'unknown':
            continue
        if p.lower()[0:3] == 'lib' and ':' in p.lower():
            continue
        for p2 in packages2:
            if p2.lower()[0:3] == 'lib' and ':' in p2.lower():
                missing_packages[p2] = False
                continue
            if packages2[p2] == 'unknown':
                missing_packages[p2] = False
                continue
            if p.lower() == p2.lower():
                # same package
                found_package = True
                missing_packages[p2] = False
                same_packages.append(p.lower())
                # same version
                if packages2[p2].lower() in packages1[p].lower() or packages1[p].lower() in packages2[p2].lower():
                    pass
                else:
                    different_versions.append((p.lower(), packages1[p].lower(), packages2[p2].lower()))
                break
        if not found_package:
            different_packages.append(p.lower())
    for m in missing_packages:
        if missing_packages[m]:
            different_packages.append(m.lower())
    tabular_similarity_info = pd.DataFrame(
            {'similar_packages': pd.Series(same_packages),
            'different_packages': pd.Series(different_packages,  dtype=str),
            'package_version1_version2': pd.Series(different_versions, dtype=str)
            })
    return tabular_similarity_info