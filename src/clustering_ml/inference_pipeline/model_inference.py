import os
import sys

from utils import CustomException
import utils
from logger import logging
import pandas as pd
import datetime 
import boto3

from dataclasses import dataclass

# Organise the classes by the highest probability
def create_order(prob, classes, k = 5):
    list_probs = list(zip(prob, classes))
    
    list_probs.sort(key = lambda x: x[0], reverse = True)

    return [element[1] for element in list_probs[:k]]

@dataclass
class ModelClusterCfg:
    if not os.path.exists('output'):
        # Create the folder if it doesn't exist
        os.makedirs('output')

    model_cluster_infos = os.path.join("models", "cluster_pipeline.json")
    model_cluster_filepath = os.path.join("models", "cluster_pipeline.pkl")
    data_filepath = os.path.join("artifacts/clustering", "processed_data.csv")
    output_inference = "output/"

    #AWS Bucket
    bucket_name = 'jooaobrum-projects'
    s3_file_path = 'crm-project/models'
    s3_client = boto3.client('s3')

class ClusterModelInference:
    def __init__(self):
        self.model_loader_config = ModelClusterCfg()

    def initiate_cluster_inference(self):
        logging.info("Model Clustering Inference Started...")
        try:
            now = datetime.datetime.now()

            # Download model from S3 bucket
            utils.download_file_from_s3(self.model_loader_config.s3_client, 
                                        self.model_loader_config.bucket_name, 
                                        os.path.join(self.model_loader_config.s3_file_path, self.model_loader_config.model_cluster_filepath.split('/')[-1]),
                                        self.model_loader_config.model_cluster_filepath.split('/')[0])
            
            # Download model info from S3
            utils.download_file_from_s3(self.model_loader_config.s3_client, 
                                        self.model_loader_config.bucket_name, 
                                        os.path.join(self.model_loader_config.s3_file_path, self.model_loader_config.model_cluster_filepath.split('/')[-1].split('.')[0] + '.json'),
                                        self.model_loader_config.model_cluster_filepath.split('/')[0])
            logging.info("Downloading model from cloud...")

            # Read the model to cluster data
            model = pd.read_pickle(self.model_loader_config.model_cluster_filepath)
            model_info = pd.read_json(self.model_loader_config.model_cluster_infos)
            logging.info("Loading completed...")

            

            # Read data to score
            df = pd.read_csv(self.model_loader_config.data_filepath)
            logging.info("Processed data read...")

            # Scoring 
            y_pred_prob = model["model"].predict_proba(df[model_info['features']])

            prob_clusters = []
            for customer in y_pred_prob:
                prob_clusters.append(create_order(customer, model["model"].classes_, k = 3))

            # Add ID
            for i in range((len(prob_clusters))):
                prob_clusters[i].insert(0, df['id'].values[i])
                prob_clusters[i].insert(0, now.strftime("%d/%m/%Y"))
            logging.info("Scoring done...")

            df_clusters = pd.DataFrame(prob_clusters, columns = ['ID', 'Date', 'Main Cluster', 'Alternative Cluster 1', 'Alternative Cluster 2'])
            df_clusters.to_csv(self.model_loader_config.output_inference + 'cluster_inference_' + now.strftime("%d%m%Y%Hh%Mm%Ss") + '.csv')
            logging.info("Saving output locally...")

            utils.upload_file_to_s3(self.model_loader_config.s3_client,
                                    self.model_loader_config.bucket_name,
                                    self.model_loader_config.output_inference + 'cluster_inference_' + now.strftime("%d%m%Y%Hh%Mm%Ss") + '.csv',
                                    os.path.join(self.model_loader_config.s3_file_path.split('/')[0], self.model_loader_config.output_inference + 'cluster_inference_' + now.strftime("%d%m%Y%Hh%Mm%Ss") + '.csv'))
            
            logging.info("Saving output on cloud...")

            os.remove(self.model_loader_config.output_inference + 'cluster_inference_' + now.strftime("%d%m%Y%Hh%Mm%Ss") + '.csv')
            logging.info("Removing output locally...")

            os.remove(self.model_loader_config.model_cluster_filepath)
            os.remove(self.model_loader_config.model_cluster_infos)
            logging.info("Removing model locally...")
           

        except Exception as e:
            raise CustomException(e, sys)