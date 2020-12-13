def closeness(j_dict1, j_dict2):
    #j_dict1 = json.load(json_res1)
    #j_dict2 = json.load(json_res2)
    packages1 = j_dict1['user_installed_packages']
    packages2 = j_dict2['user_installed_packages']
    same_packges = 0
    similar_packges = list()
    for p in packages1:
        for p2 in packages2:
            if p.lower() in p2.lower() or p2.lower() in p.lower():
                # same package
                same_packges += 1
                similar_packges.append((p.lower(), packages1[p].lower(), p2.lower(), packages2[p2].lower()))
                # same version
                if packages2[p2].lower() in packages1[p].lower() or packages1[p].lower() in packages2[p2].lower():
                    same_packges += 1
                break
    min_len = len(packages1) if len(packages1) > len(packages2) else len(packages2)
    return same_packges/ (min_len*2)