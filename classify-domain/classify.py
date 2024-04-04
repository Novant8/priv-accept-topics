import argparse
import json
from tflite_support.task import text, core
import os

parser = argparse.ArgumentParser()
parser.add_argument('domain', type=str)
parser.add_argument('--model', type=str, default='model.tflite')
parser.add_argument('--model_info', type=str, default='model-info.pb')
parser.add_argument('--override_list', type=str, default='override_list.pb')
parser.add_argument('--models_proto', type=str, default='models.proto')
parser.add_argument('--common_types_proto', type=str, default='common_types.proto')
parser.add_argument('--model_metadata_proto', type=str, default='page_topics_model_metadata.proto')
parser.add_argument('--override_list_proto', type=str, default='page_topics_override_list_proto.proto')
parser.add_argument('--proto_path', type=str, default='.')
parser.add_argument('--map_topics', action='store_true')
parser.add_argument('--topics_map_file', type=str, default='topic_mapping.json')

args = parser.parse_args()

for proto_file in [ args.common_types_proto, args.models_proto, args.model_metadata_proto, args.override_list_proto ]:
  os.system("protoc {} --proto_path {} --python_out .".format(proto_file, args.proto_path))

import models_pb2
import page_topics_override_list_pb2
import page_topics_model_metadata_pb2

NONE_CATEGORY = "-2"

def read_override_list():
    # Read the existing address book.
    override_list = page_topics_override_list_pb2.PageTopicsOverrideList()
    try:
      with open(args.override_list, "rb") as file:
        override_list.ParseFromString(file.read())
      return override_list
    except IOError:
      print("Could not read file {}.".format(args.override_list))
      exit(1)

def read_model_metadata():
    model_info = models_pb2.ModelInfo()
    try:
      with open(args.model_info, "rb") as file:
        model_info.ParseFromString(file.read())
    except IOError:
      print("Could not read file {}".format(args.model_info))
      exit(1)

    # Read the existing address book.
    model_metadata = page_topics_model_metadata_pb2.PageTopicsModelMetadata()
    try:
      model_metadata.ParseFromString(model_info.model_metadata.value)
      return model_metadata
    except AttributeError:
       print("Could not extract model metadata from model info")
       exit(1)

# Replaces a set of common domain characters with white space. See https://source.chromium.org/chromium/chromium/src/+/main:components/optimization_guide/core/page_topics_model_executor.cc;l=211?q=meaningless%20f:optimization_guide&ss=chromium
def process_domain(domain):
  replace_chars = ['-', '_', '.', '+']
  for rc in replace_chars:
    domain = domain.replace(rc, " ")
  return domain

def check_override_list(override_list, domain):
  if override_list is None:
    return None
  for entry in override_list.entries:
    if entry.domain == domain:
      return entry.topics.topic_ids
  return None

def infer_from_model(domain, model, category_params):
    def CategorySort(elem):
      return elem.score

    topics = model.classify(domain)
    categories = sorted(topics.classifications[0].categories, key=CategorySort)[-category_params.max_categories:][::-1]
    
    # POST-PROCESS CATEGORIES
    none_weight = None
    total_weight = 0
    sum_positive_scores = 0
    for category in categories: 
      total_weight += category.score
      if category.score > 0:
        sum_positive_scores += category.score
      if category.category_name == NONE_CATEGORY:
        none_weight = category.score

    # Prune out categories that do not meet the minimum threshold.
    if category_params.min_category_weight > 0:
       categories = [ c for c in categories if c.score >= category_params.min_category_weight ]
    
    # Prune out none weights
    if none_weight:
      if (none_weight / total_weight) <= category_params.min_none_weight:
        # None weight is too strong
        return []
      
      # None weight doesn't matter, so prune it out.
      categories = [ c for c in categories if c.category_name != NONE_CATEGORY ]

    # Normalize category weights
    normalization_factor = sum_positive_scores if sum_positive_scores > 0 else 1
    categories = [ c for c in categories if (c.score / normalization_factor) >= category_params.min_normalized_weight_within_top_n ]

    return [ c.category_name for c in categories ]

def get_topics_from_domain(domain, model, override_list, model_metadata):
    processed_domain = process_domain(domain)
    topics = check_override_list(override_list, processed_domain)
    if topics != None:
        return [ str(t) for t in topics ]
    else:
        return infer_from_model(processed_domain, model, model_metadata.output_postprocessing_params.category_params)  

def main():
    override_list = read_override_list()
    model_metadata = read_model_metadata()

    options = text.BertNLClassifierOptions(base_options=core.BaseOptions(file_name=args.model))
    tflite_topics = text.BertNLClassifier.create_from_options(options)

    topics = get_topics_from_domain(args.domain, model=tflite_topics, override_list=override_list, model_metadata=model_metadata)

    if args.map_topics:
      try:
        with open(args.topics_map_file, "r") as file:
          topics_map = json.load(file)
        topics = [ topics_map[topic] for topic in topics ]
      except IOError:
         print("Could not read file {}.".format(args.topics_map))

    print("{},{}".format(args.domain, ",".join(topics)))

if __name__ == '__main__':
    main()