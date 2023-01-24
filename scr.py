import json
import yaml
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", dest = "input_file")
parser.add_argument("-o", "--output", dest = "output_file")
args = parser.parse_args()

def print_results(api_name, found_methods, par_cnt):
    print("Api Name - " + api_name)
    print(count_duplicates(found_methods)) 
    print("Method Count - " + str(len(found_methods)))
    print("Parameter Count - " + str(par_cnt))
    print("----------------")


def count_duplicates(lst):
    counts = {}
    for i in lst:
        if i in counts:
            counts[i] += 1
        else:
            counts[i] = 1
    duplicates = {k:v for k,v in counts.items() if v >= 1}
    return duplicates

def get_parameter_count(data):
    cnt = 0
    cnt += len(data["header"]) 
    cnt += (len(data["body"]) if "body" in data else 0)
    cnt += len(data["url"]["variable"]) 
    cnt += (len(data["url"]["query"]) if "query" in data["url"] else 0)
    return cnt

def recursive_methods(data, found_methods, par_cnt):
    if "item" in data:
        for x in data["item"]:
            par_cnt = recursive_methods(x, found_methods, par_cnt)
    else:
        if "request" in data:
            found_methods.append(data["request"]["method"])
            par_cnt += get_parameter_count(data["request"])
    return par_cnt
       
def base_json(file_data):
    for api in file_data["item"]:
        found_methods = []
        par_cnt = 0
        par_cnt = recursive_methods(api, found_methods, par_cnt)
        print_results(api["name"], found_methods, par_cnt)

def swaggerJsonYaml(data):
    found_methods = []
    par_cnt = 0
    for path in data["paths"]:
        for method in data["paths"][path]:
            found_methods.append(method)
            par_cnt += len(data["paths"][path][method]["parameters"])
    print_results(data["info"]["title"], found_methods, par_cnt)

def gotJson(data):
    if "swagger" in data:
        print("Found matching json swagger format, proceeding...")
        swaggerJsonYaml(data)
        return
    if "_postman_id" in data["info"]:
        print("Found matching json postman format, proceeding...")
        base_json(data)
        return
    print("Unrecognized format")

def main():
    try:
        with open(args.input_file) as f:
            data = json.load(f)
            gotJson(data)
            return
    except json.JSONDecodeError:
        print("Not json, trying yaml")
    try:
        with open(args.input_file) as f:
            data = yaml.safe_load(f)
            swaggerJsonYaml(data)
            return
    except yaml.YAMLError:
        print("Not yaml either")


if __name__=="__main__":
    main()

