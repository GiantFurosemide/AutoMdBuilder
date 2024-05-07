"""
RDKit is required to run this script.
> conda activate my-rdkit-env

input: csv file with a column of SMILES strings with name 'smile_string'
output: csv file with two columns of mass and logP appended to the input csv file
"""



from rdkit import Chem
from rdkit.Chem import Descriptors
import pandas as pd



def smile2mass(smile_str) -> float:
    molecule = Chem.MolFromSmiles(smile_str)
    mass = Descriptors.ExactMolWt(molecule)
    #print(f">{smile_str} \n> Molecular Weight: {mass}")
    return mass


def smile2logP(smile_str) -> float:
    molecule = Chem.MolFromSmiles(smile_str)
    logP = Descriptors.MolLogP(molecule)
    #print(f">{smile_str} \n> logP: {logP}")
    return logP

# read csv file by pandas. calucate mass and logP for each SMILES string 
def csv_append_mass_logP(csv_file)-> pd.DataFrame:
    df = pd.read_csv(csv_file)
    df['mass'] = df['smile_string'].apply(smile2mass)
    df['logP'] = df['smile_string'].apply(smile2logP)
    return df

#save the dataframe to csv file
def save_csv(df, csv_file):
    df.to_csv(csv_file, index=False)
    print(f"Saved to {csv_file}")

# plot scatter plot for mass and logP.save as png file with name 'mass_logP.png'
def plot_mass_logP(df):
    import matplotlib.pyplot as plt
    plt.scatter(df['mass'], df['logP'])
    plt.xlabel('Mass')
    plt.ylabel('logP')
    #plt.show()
    plt.savefig('mass_logP.png')
    plt.clf()

# plot pie chart for mass. save as png file with name 'mass_pie.png'
def plot_mass_pie(df):
    import matplotlib.pyplot as plt
    plt.pie(df['mass'], labels=df['smile_string'], autopct='%1.1f%%')
    #plt.show()
    plt.savefig('logP_pie.png')

# plot logP chart for mass. 
# save as png file with name 'logP_pie.png'
# split the range of the value of logP into 5 bins
def plot_logP_pie(df):
    import matplotlib.pyplot as plt
    plt.pie(df['logP'], labels=df['smile_string'], autopct='%1.1f%%')
    #plt.show()
    plt.savefig('logP_pie.png')

# plot histogram for mass. save as png file with name 'mass_hist.png'
# split the range of the value of mass into 5 bins
def plot_mass_hist(df):
    import matplotlib.pyplot as plt
    plt.hist(df['mass'], bins=10)
    plt.xlabel('Mass')
    plt.ylabel('Frequency')
    #plt.show()
    plt.savefig('mass_hist.png')
    plt.clf()

# plot histogram for logP. save as png file with name 'logP_hist.png'
# split the range of the value of logP into 5 bins
def plot_logP_hist(df):
    import matplotlib.pyplot as plt
    plt.hist(df['logP'], bins=10)
    #print(df['logP'])
    plt.xlabel('logP')
    plt.ylabel('Frequency')
    #plt.show()
    plt.savefig('logP_hist.png')
    plt.clf()


if __name__ == "__main__":
    
    csv_file = 'output.csv'
    df = csv_append_mass_logP(csv_file)
    save_csv(df, 'smiles_mass_logP.csv')

    plot_mass_logP(df)
    #plot_mass_pie(df)
    #plot_logP_pie(df)
    plot_mass_hist(df)
    plot_logP_hist(df)
    print("Done")