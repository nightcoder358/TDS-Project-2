import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import httpx
import chardet
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
AIPROXY_TOKEN = os.getenv('eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIzZjMwMDQzNzJAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.rkHKbsNhGyk2QNEMd3REyMbqJw9TvaOqUOsV8vWWDa0')  # Fetch token from environment variable

def load_data(file_path):
    """Load CSV data with encoding detection."""
    print(f"Loading data from {file_path}...")
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    encoding = result['encoding']
    return pd.read_csv(file_path, encoding=encoding)

def analyze_data(df):
    """Perform basic data analysis."""
    print("Performing basic data analysis...")
    numeric_df = df.select_dtypes(include=['number'])  # Select only numeric columns
    analysis = {
        'summary': df.describe(include='all').to_dict(),
        'missing_values': df.isnull().sum().to_dict(),
        'correlation': numeric_df.corr().to_dict()  # Compute correlation only on numeric columns
    }

    # Perform clustering
    df_with_clusters = perform_clustering(df)
    analysis['clustering'] = df_with_clusters['Cluster'].value_counts().to_dict()  # Show clustering distribution

    return analysis

def perform_clustering(df):
    """Perform clustering on the numeric columns."""
    print("Performing clustering...")
    numeric_df = df.select_dtypes(include=['number'])  # Select only numeric columns

    # Step 1: Handle missing values by imputing the mean of each column
    imputer = SimpleImputer(strategy='mean')
    numeric_df_imputed = imputer.fit_transform(numeric_df)

    # Step 2: Perform KMeans clustering
    kmeans = KMeans(n_clusters=3, random_state=42)
    clusters = kmeans.fit_predict(numeric_df_imputed)

    # Add the cluster labels as a new column in the original dataframe
    df['Cluster'] = clusters
    return df

def visualize_data(df, dataset_name):
    """Generate and save visualizations."""
    print(f"Generating visualizations for {dataset_name}...")
    sns.set(style="whitegrid")
    numeric_columns = df.select_dtypes(include=['number']).columns  # Only include numeric columns
    for column in numeric_columns:
        plt.figure()
        sns.histplot(df[column].dropna(), kde=True)
        plt.title(f'Distribution of {column}')
        plt.savefig(f'{dataset_name}_{column}_distribution.png')
        plt.close()

    # Correlation heatmap
    print(f"Generating correlation heatmap for {dataset_name}...")
    numeric_df = df.select_dtypes(include=['number'])  # Only include numeric columns
    if not numeric_df.empty:  # Check if there are any numeric columns
        plt.figure(figsize=(10, 8))
        sns.heatmap(numeric_df.corr(), annot=True, cmap='coolwarm', fmt='.2f')
        plt.title(f'Correlation Matrix of {dataset_name}')
        plt.savefig(f'{dataset_name}_correlation_matrix.png')
        plt.close()
    else:
        print(f"No numeric data available for correlation in {dataset_name}.")

def generate_narrative(analysis, dataset_name):
    """Generate narrative using LLM."""
    print(f"Generating narrative for {dataset_name}...")
    headers = {
        'Authorization': f'Bearer {AIPROXY_TOKEN}',
        'Content-Type': 'application/json'
    }
    prompt = f"Provide a detailed analysis based on the following data summary for {dataset_name}: {analysis}"
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = httpx.post(API_URL, headers=headers, json=data, timeout=30.0)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
    except httpx.RequestError as e:
        print(f"Request error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return "Narrative generation failed due to an error."

def main():
    # Get the current directory
    current_directory = os.getcwd()

    # Get all CSV files in the directory
    csv_files = [f for f in os.listdir(current_directory) if f.endswith('.csv')]

    # If no CSV files are found, exit
    if not csv_files:
        print("No CSV files found in the directory.")
        return

    for file in csv_files:
        print(f"\nProcessing {file}...")
        df = load_data(file)
        analysis = analyze_data(df)
        visualize_data(df, file.split('.')[0])  # Use the file name without extension for output
        narrative = generate_narrative(analysis, file.split('.')[0])

        # Save the narrative as README.md in a folder named after the dataset
        dataset_folder = file.split('.')[0]
        os.makedirs(dataset_folder, exist_ok=True)  # Create a folder for the dataset
        with open(os.path.join(dataset_folder, 'README.md'), 'w') as f:
            f.write(narrative)

        print(f"Analysis for {file} completed!\n")

if __name__ == "__main__":
    main()
