---
license: apache-2.0
language:
- en
- am
- ig
- fr
- sn
- ln
- lug
- wo
- ee
- xh
- kin
- tw
- zu
- orm
- yo
- ha
- sot
- sw
size_categories:
- n<1K
multilinguality:
- multilingual
pretty_name: afrixnli
language_details: eng, amh, ibo, fra, sna, lin, wol, ewe, lug, xho, kin, twi, zul, orm, yor, hau, sot, swa
source_datasets:
- xnli
tags:
- afrixnli
- afri-xnli
- africanxnli
task_categories:
- text-classification
task_ids:
- natural-language-inference
configs:
- config_name: amh
  data_files:
  - split: validation
    path: data/amh/dev.tsv
  - split: test
    path: data/amh/test.tsv
- config_name: eng
  data_files:
  - split: validation
    path: data/eng/dev.tsv
  - split: test
    path: data/eng/test.tsv
- config_name: ewe
  data_files:
  - split: validation
    path: data/ewe/dev.tsv
  - split: test
    path: data/ewe/test.tsv
- config_name: fra
  data_files:
  - split: validation
    path: data/fra/dev.tsv
  - split: test
    path: data/fra/test.tsv
- config_name: hau
  data_files:
  - split: validation
    path: data/hau/dev.tsv
  - split: test
    path: data/hau/test.tsv
- config_name: ibo
  data_files:
  - split: validation
    path: data/ibo/dev.tsv
  - split: test
    path: data/ibo/test.tsv
- config_name: kin
  data_files:
  - split: validation
    path: data/kin/dev.tsv
  - split: test
    path: data/kin/test.tsv
- config_name: lin
  data_files:
  - split: validation
    path: data/lin/dev.tsv
  - split: test
    path: data/lin/test.tsv
- config_name: lug
  data_files:
  - split: validation
    path: data/lug/dev.tsv
  - split: test
    path: data/lug/test.tsv
- config_name: orm
  data_files:
  - split: validation
    path: data/orm/dev.tsv
  - split: test
    path: data/orm/test.tsv
- config_name: sna
  data_files:
  - split: validation
    path: data/sna/dev.tsv
  - split: test
    path: data/sna/test.tsv
- config_name: sot
  data_files:
  - split: validation
    path: data/sot/dev.tsv
  - split: test
    path: data/sot/test.tsv
- config_name: swa
  data_files:
  - split: validation
    path: data/swa/dev.tsv
  - split: test
    path: data/swa/test.tsv
- config_name: twi
  data_files:
  - split: validation
    path: data/twi/dev.tsv
  - split: test
    path: data/twi/test.tsv
- config_name: wol
  data_files:
  - split: validation
    path: data/wol/dev.tsv
  - split: test
    path: data/wol/test.tsv
- config_name: xho
  data_files:
  - split: validation
    path: data/xho/dev.tsv
  - split: test
    path: data/xho/test.tsv
- config_name: yor
  data_files:
  - split: validation
    path: data/yor/dev.tsv
  - split: test
    path: data/yor/test.tsv
- config_name: zul
  data_files:
  - split: validation
    path: data/zul/dev.tsv
  - split: test
    path: data/zul/test.tsv
    
---

# Dataset Card for afrixnli

## Table of Contents
- [Table of Contents](#table-of-contents)
- [Dataset Description](#dataset-description)
  - [Dataset Summary](#dataset-summary)
  - [Languages](#languages)
- [Dataset Structure](#dataset-structure)
  - [Data Instances](#data-instances)
  - [Data Fields](#data-fields)
  - [Data Splits](#data-splits)
 
## Dataset Description

- **Point of Contact:** d.adelani@ucl.ac.uk

### Dataset Summary

AFRIXNLI is an evaluation dataset comprising translations of a subset of the XNLI dataset into 16 African languages. 
It includes both validation and test sets across all 18 languages, maintaining the English and French subsets from the original XNLI dataset. 

### Languages

There are 18 languages available :

## Dataset Structure

### Data Instances

The examples look like this for English:

```
from datasets import load_dataset
data = load_dataset('masakhane/afrixnli', 'eng') 
# Please, specify the language code
# A data point example is below:
{
'premise': 'The doors were locked when we went in.',
'hypothesis': 'All of the doors were open.',
'label': 0
}
```

### Data Fields

- `premise`: a multilingual string variable,
- `hypothesis`: a multilingual string variable,
- `label`: a classification label, with possible values including entailment (0), neutral (1), contradiction (2).

### Data Splits

All languages has two splits, `dev` and `test` a subset of the original `dev` and `test` splits of the XNLI dataset.

The splits have the following sizes :

| Language        | validation | test |
|-----------------|-----------:|-----:|
| English         |        450 |  600 |