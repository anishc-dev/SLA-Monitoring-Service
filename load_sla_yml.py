import yaml

def load_sla_yml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

if __name__ == "__main__":
    print(load_sla_yml("sla_config.yml"))