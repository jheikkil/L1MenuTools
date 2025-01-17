import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import tempfile
import argparse
import wget
import random

# define CLI elements
parser = argparse.ArgumentParser()
parser.add_argument(
    "--rateTable",
    help="Existing rate table",
    default="example-inputs/output_Run2unpacked.csv",
    type=str,
)
parser.add_argument(
    "--output",
    help="Name of created output file",
    default="rates",
    type=str,
)
parser.add_argument(
    "--rate",
    help="Type of rate used in plots",
    default="propotional0",
    type=str,
)
args = parser.parse_args()

csv_rate_table = args.rateTable
rateType = args.rate
outputFolder = "output/"
outputFileName = os.path.join(outputFolder, args.output)
if not os.path.exists(outputFolder):
    os.makedirs(outputFolder)

if not os.path.exists(csv_rate_table):
    os.system(
        "wget https://raw.githubusercontent.com/cms-l1-dpg/L1MenuTools/master/piechart-tool/{}".format(
            csv_rate_table
        )
    )
else:
    print("Rate table exists, no need to download it")

# reading the rate table
df = pd.read_csv(csv_rate_table, sep=",")


# preparing a dataframe with PS==1 seeds only (only for the sake of this example), using some Boolean slicing of the df dataframe
df_PS1 = df[df["pre-scale0"] >= 1]
df_PS = df[df["pre-scale0"] > 1]

# definition of one of the categorization functions
# (mind the extra @np.vectorize decorator - this is necessary to parallelize the function application call for entire columns later on)
@np.vectorize
def isSingleMuSeed(seedname):
    identifiers = ["SingleMu"]
    vetoes = ["Jet", "EG", "Tau", "ETM", "HTT", "ETT", "ETMHF", "ZeroBias"]
    return all([identifier in seedname for identifier in identifiers]) and not any(
        [veto in seedname for veto in vetoes]
    )


@np.vectorize
def isMultiMuSeed(seedname):
    identifiers = ["DoubleMu", "TripleMu", "QuadMu"]
    vetoes = ["Jet", "EG", "Tau", "ETM", "HTT", "ETT", "ETMHF", "ZeroBias"]
    return any([identifier in seedname for identifier in identifiers]) and not any(
        [veto in seedname for veto in vetoes]
    )


@np.vectorize
def isMuEGSeed(seedname):
    identifiers = ["Mu", "EG"]
    vetoes = ["Jet", "Tau", "ETM", "HTT", "ETT", "ETMHF", "ZeroBias"]
    return all([identifier in seedname for identifier in identifiers]) and not any(
        [veto in seedname for veto in vetoes]
    )


@np.vectorize
def isMuJetSeed(seedname):
    identifiers = ["Mu"]
    Jetsums = ["Jet", "ETM", "HTT", "ETT", "ETMHF"]
    vetoes = ["EG", "Tau", "ZeroBias"]
    return (
        all([identifier in seedname for identifier in identifiers])
        and any([Sum in seedname for Sum in Jetsums])
        and not any([veto in seedname for veto in vetoes])
    )


@np.vectorize
def isSingleEGSeed(seedname):
    identifiers = [
        "SingleEG",
        "SingleIsoEG",
        "SingleLooseEG",
        "SingleLooseIsoEG",
        "IsoEG",
    ]
    # EGsums = ["Single","Iso"]
    vetoes = ["Jet", "Mu", "Tau", "ETM", "HTT", "ETT", "ETMHF", "ZeroBias", "Double"]
    return any([identifier in seedname for identifier in identifiers]) and not any(
        [veto in seedname for veto in vetoes]
    )


@np.vectorize
def isMultiEGSeed(seedname):
    identifiers = ["DoubleEG", "TripleEG", "DoubleIsoEG", "DoubleLooseIsoEG"]
    vetoes = ["Jet", "Mu", "Tau", "ETM", "HTT", "ETT", "ETMHF", "ZeroBias"]
    return any([identifier in seedname for identifier in identifiers]) and not any(
        [veto in seedname for veto in vetoes]
    )


@np.vectorize
def isEGJetSeed(seedname):
    identifiers = ["EG"]
    Jetsums = ["Jet", "ETM", "HTT", "ETT", "ETMHF"]
    vetoes = ["Mu", "Tau", "ZeroBias"]
    return (
        all([identifier in seedname for identifier in identifiers])
        and any([Sum in seedname for Sum in Jetsums])
        and not any([veto in seedname for veto in vetoes])
    )


@np.vectorize
def isJetSeed(seedname):
    identifiers = ["Jet"]
    vetoes = ["EG", "Mu", "Tau", "ETM", "HTT", "ETT", "ETMHF", "ZeroBias"]
    return all([identifier in seedname for identifier in identifiers]) and not any(
        [veto in seedname for veto in vetoes]
    )


@np.vectorize
def isTauSeed(seedname):
    identifiers = ["Tau"]
    vetoes = ["EG", "Mu", "Jet", "ETM", "HTT", "ETT", "ETMHF", "ZeroBias"]
    return all([identifier in seedname for identifier in identifiers]) and not any(
        [veto in seedname for veto in vetoes]
    )


@np.vectorize
def isLepJetSeed(seedname):
    identifiers = ["Tau"]
    Jetsums = ["Jet", "Mu", "EG", "ETM", "HTT", "ETT", "ETMHF"]
    vetoes = ["ZeroBias"]
    return (
        all([identifier in seedname for identifier in identifiers])
        and any([Sum in seedname for Sum in Jetsums])
        and not any([veto in seedname for veto in vetoes])
    )


@np.vectorize
def isSumsSeed(seedname):
    identifiers = ["Jet"]
    Jetsums = ["ETM", "HTT", "ETT", "ETMHF"]
    vetoes = ["EG", "Mu", "Tau", "ZeroBias"]
    return any([Sum in seedname for Sum in Jetsums]) and not any(
        [veto in seedname for veto in vetoes]
    )


@np.vectorize
def isZeroBiasSeed(seedname):
    identifiers = ["ZeroBias"]
    vetoes = ["EG", "Mu", "Tau", "Jet", "ETM", "HTT", "ETT", "ETMHF"]
    return all([identifier in seedname for identifier in identifiers]) and not any(
        [veto in seedname for veto in vetoes]
    )


@np.vectorize
def isCalibrationSeed(seedname):
    # function is intended for use with PS > 1 seeds only
    identifiers = [
        "EG",
        "Mu",
        "Tau",
        "Jet",
        "ETM",
        "HTT",
        "ETT",
        "ETMHF",
        "ZeroBias",
        "Bunch",
        "Train",
    ]
    return any([identifier in seedname for identifier in identifiers])


functions = {
    "isSingleMuSeed": isSingleMuSeed,
    "isMultiMuSeed": isMultiMuSeed,
    "isMuEGSeed": isMuEGSeed,
    "isSingleEGSeed": isSingleEGSeed,
    "isMuJetSeed": isMuJetSeed,
    "isSingleEGSeed": isSingleEGSeed,
    "isMultiEGSeed": isMultiEGSeed,
    "isEGJetSeed": isEGJetSeed,
    "isJetSeed": isJetSeed,
    "isTauSeed": isTauSeed,
    "isLepJetSeed": isLepJetSeed,
    "isSumsSeed": isSumsSeed,
    "isZeroBiasSeed": isZeroBiasSeed,
    "isCalibrationSeed": isCalibrationSeed,
}
# ... define the rest of the functions here, one for each category...
# extend the dataframe with new columns that contain the return values of the specific categorization functions
# thanks to the no.vectorize decorator in the function definition, pandas knows to run this "row-by-row" internally
# if df_PS1["PS"].all() == 1:
for category in [
    "isSingleMu",
    "isMultiMu",
    "isMuEG",
    "isMuJet",
    "isSingleEG",
    "isMultiEG",
    "isEGJet",
    "isJet",
    "isTau",
    "isLepJet",
    "isSums",
    "isZeroBias",
]:  # can be later extended ["isSingleMu", "isMultiMu",...]
    func = category + "Seed"
    function = functions[func]
    df_PS1[category] = function(df_PS1["L1SeedName"])

df_PS["isCalibration"] = isCalibrationSeed(df_PS["L1SeedName"])
# if df_PS1["PS"].all() > 1:
# df_PS1["isCalibration"] = isCalibrationSeed(df_PS1["L1SeedName"])

# inspect the newly added column(s)
# df_PS1

# Eventually, one should also automatically check and make sure that there is
# only one "True" value per row for each row in the dataframe (ie, each seed
# can only be in a single category)!

# Example: inspect all (PS==1) seeds that have been identified as SingleMu seeds
# df_PS1[df_PS1["isSingleMu"] == True]
# df_PS1[df_PS1["isSingleEG"] == True]
# df_PS[df_PS["isCalibration"] == True]

# extracting the sum of proportional rates for all seeds which have isSingleMu == True
# in this dummy example, we should add up 3960.02 + 2610.46 = 6570.48
sums = {}
# for rate_type in ["rate0", "pure0", "propotional0"]:
for rate_type in ["{}".format(rateType)]:
    sums[rate_type] = {}
    # calculating calibration for PS_rate as done in Aloke's script
    # sums[rate_type]["isCalibration"] = (df_PS[df_PS["isCalibration"] == True][rate_type]).sum()
    sums[rate_type]["isCalibration"] = (
        df_PS[df_PS["isCalibration"] == True]["rate0"]
    ).sum()
    for category in [
        "isSingleMu",
        "isMultiMu",
        "isMuEG",
        "isMuJet",
        "isSingleEG",
        "isMultiEG",
        "isEGJet",
        "isJet",
        "isTau",
        "isLepJet",
        "isSums",
        "isZeroBias",
    ]:  # can be extended later: ["isSingleMu", "isMultiMu",...]
        sums[rate_type][category] = (df_PS1[df_PS1[category] == True][rate_type]).sum()
sumCalib = {}
for rate_type in ["{}".format(rateType)]:
    # for rate_type in ["rate0", "pure0", "propotional0"]:
    sumCalib[rate_type] = {}
    sumCalib[rate_type]["isCalibration"] = (
        df_PS[df_PS["isCalibration"] == True][rate_type]
    ).sum()
# check the results
# from pprint import pprint

# pprint(sums)
# pprint(sumCalib)

# once all rates have been extracted per category and (probably best) stored in
# a separate data structure (like in the dictionary above), one can go to the
# plotting step...
labels = []
rates = []
percnt = []
for x, y in sums["{}".format(rateType)].items():
    print("{}: ".format(rateType), x, y)
    labels.append(x[2:])
    rates.append(y)
# for x, y in sums["rate0"].items():
#    print("pure rate: ", x, y)

wedges, lab, pct_text = plt.pie(
    rates,
    labels=labels,
    autopct="%1.1f%%",
    labeldistance=1.0,
    pctdistance=0.6,
    rotatelabels=True,
    colors=plt.cm.tab20.colors,
)
# wedges, lab, pct_text=plt.pie(rates, labels=labels, autopct="%1.1f%%", labeldistance=1.0, pctdistance=0.6, rotatelabels=True, colors=mcolors.TABLEAU_COLORS)
for label, pct_text in zip(lab, pct_text):
    pct_text.set_rotation(label.get_rotation())

plt.axis("equal")
fig = plt.gcf()
fig.tight_layout()
ext = ["png", "pdf"]
for e in ext:
    fig.savefig("{}_pieChart.{}".format(outputFileName, e), transparent=True)
    print("File saved: {}_pieChart.{}".format(outputFileName, e))

## for getting percentages
tot = sum(rates)
# print ("sum of all rate: ", tot)
figbar, ax = plt.subplots(figsize=(10, 5))
ax.barh(labels, rates, edgecolor="black", color="None", align="center", alpha=0.5)
for i, v in enumerate(rates):
    ax.text(
        v,
        i,
        "{:.1f}{}".format((v / tot) * 100, "%"),
        horizontalalignment="left",
        color="black",
        va="center",
        fontweight="bold",
    )
    ax.text(v, i, "             {:.1f} Hz".format(v), color="black", va="center")
    ## rates in percentages displyed within the bars of plot, not the best solution , as they get jumbled up when the bar is too small
    # ax.text(v*0.1 , i, '  {:.1f}{}'.format((v/tot)*100,'%'),horizontalalignment='left', color='black', va='center', fontweight='bold')
plt.ylabel("Seeds")
plt.xlabel("Rates of Seeds")
plt.title(
    "L1 Rates for Seed Categories\n(Total rate: {:.2f} kHz)".format(df_PS1.iloc[-1, 3])
)
plt.box(False)
ax.get_xaxis().set_ticks([])
# ax.axis('off')
barfig = plt.gcf()
barfig.tight_layout()
for e in ext:
    barfig.savefig("{}_barPlot.{}".format(outputFileName, e), transparent=True)
    print("File saved: {}_barPlot.{}".format(outputFileName, e))

# print ("last line of df: ", df_PS1.iloc[-1,3])
# df_PS1[df_PS1["isSingleEG"] == True]
df_PS1[df_PS1["isMultiEG"] == True]

# make sure that each seed is in only one category
for i in range(len(df_PS1)):
    if list((df_PS1.iloc[i][7:])).count(True) > 1:
        # if list((df_PS1.iloc[i][7:])).count(True) == 0:
        # print ( (df_PS1.iloc[i][7:]) )
        print(
            "Inconsistent categorization: {} PS1: {}, prop_rate: {}".format(
                (df_PS1.iloc[i, 1]), df_PS1.iloc[i, 2], df_PS1.iloc[i, 6]
            )
        )
