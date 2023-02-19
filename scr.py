import json
import yaml
import argparse
import glob
import os

parser = argparse.ArgumentParser()
#parser.add_argument("-i", "--input", dest = "input_file")
parser.add_argument("-i", "--input", type=str, nargs="+", dest="input")
parser.add_argument("-d", "--dir", type=str, dest="dir")
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

# preload swagger parameters https://swagger.io/docs/specification/components/
def swaggerParPreload(data):
    par_dict = {}
    definitions = data.get("definitions", {}) # 2.0 support
    for key, value in definitions.items():
        properties = value.get("properties", None)
        par_dict[key] = len(properties) if properties else 1

    schemas = data.get("components", {}).get("schemas", {}) # 3.0 support
    for key, value in schemas.items():
        properties = value.get("properties", None)
        par_dict[key] = len(properties) if properties else 1

    parameters = data.get("components", {}).get("parameters", {}) # 3.0 support
    for key, value in parameters.items():
        par_schema = value.get("schema", None)
        if "$ref" in par_schema:
            last_word = par_schema["$ref"].split("/")[-1]
            par_dict[key] = par_dict[last_word] if par_schema else 1
        else:
            par_dict[key] = 1

    requestBodies = data.get("components", {}).get("requestBodies", {}) # 3.0 support
    for key, value in requestBodies.items():
        req_content = value.get("content", {})
        for content_type, content_value in req_content.items():
            if "oneOf" in content_value["schema"]:
                for x in content_value["schema"]["oneOf"]:
                    last_word = x["$ref"].split("/")[-1]
                    par_dict[key] = par_dict[last_word] if "$ref" in x else 1
            else:
                last_word = content_value["schema"]["$ref"].split("/")[-1]
                par_dict[key] = par_dict[last_word] if "$ref" in content_value["schema"] else 1

    #print(par_dict)
    return par_dict

def swaggerParMatch(parameter, par_dict):
    cnt = 0
    for x in parameter:
        if "$ref" in x:
           # print(x)
            last_word = x["$ref"].split("/")[-1]
            cnt += par_dict[last_word]
        elif "schema" in x and "$ref" in x["schema"]:
            last_word = x["schema"]["$ref"].split("/")[-1]
            cnt += par_dict[last_word]
        else:
            cnt += 1
    return cnt 

def swaggerParMatchRequestBody(parameter, par_dict):
    cnt = 0
    if "$ref" in parameter:
        last_word = parameter["$ref"].split("/")[-1]
        cnt += par_dict[last_word]
    elif "content" in parameter:
        for reqBody in parameter["content"]:
            last_word = parameter["content"][reqBody]["schema"]["$ref"].split("/")[-1]
            cnt += par_dict[last_word]
    else:
        cnt+=1

    return cnt 

def swaggerJsonYaml(data):
    par_dict = swaggerParPreload(data)
    found_methods = []
    par_cnt = 0
    for path in data["paths"]:
        for method in data["paths"][path]:
            found_methods.append(method)
            par_cnt += swaggerParMatch(data["paths"][path][method]["parameters"], par_dict)
            if "requestBody" in data["paths"][path][method]:
                try:
                    par_cnt += swaggerParMatchRequestBody(data["paths"][path][method]["requestBody"], par_dict)
                except Exception as e:
                    print(f"Error occured during requestBody count, count might not be accurate - {e}")
            #par_cnt += len(data["paths"][path][method]["parameters"])
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

def multipleFiles(filename):
    print('File: ', filename)
    try:
        with open(filename, encoding="utf-8") as f:
            data = json.load(f)
            gotJson(data)
            return
    except json.JSONDecodeError:
        print("Not json, trying yaml")
    try:
        with open(filename, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            swaggerJsonYaml(data)
            return
    except yaml.YAMLError:
        print("Not yaml either")


def main():
    for input_path in args.input:
        if os.path.isdir(input_path):
            print("Folder ", input_path)
            files_from_dir = glob.glob(input_path + "/*")
            for file in files_from_dir:
                multipleFiles(file)
        else:
            multipleFiles(input_path)
        print("\n")


if __name__=="__main__":
    main()

