---
license: apache-2.0
language:
- am
- ee
- ha
- ig
- kin
- ln
- lug
- orm
- sna
- sot
- tw
- wo
- xh
- yo
- zu
- en
- fr
- sw
size_categories:
- n<1K
multilinguality:
- multilingual
pretty_name: afrimmlu
language_details: >-
  eng, amh, ibo, fra, sna, lin, wol, ewe, lug, xho, kin, twi, zul, orm, yor,
  hau, sot, swa
source_datasets:
- mmlu
tags:
- afrimmlu
- afri-mmlu
- africanmmlu
task_categories:
- question-answering
task_ids:
- multiple-choice-qa
configs:
- config_name: amh
  data_files:
  - split: validation
    path: data/amh/val.tsv
  - split: dev
    path: data/amh/dev.tsv
  - split: test
    path: data/amh/test.tsv
- config_name: eng
  data_files:
  - split: validation
    path: data/eng/val.tsv
  - split: dev
    path: data/eng/dev.tsv
  - split: test
    path: data/eng/test.tsv
- config_name: ewe
  data_files:
  - split: validation
    path: data/ewe/val.tsv
  - split: dev
    path: data/ewe/dev.tsv
  - split: test
    path: data/ewe/test.tsv
- config_name: fra
  data_files:
  - split: validation
    path: data/fra/val.tsv
  - split: dev
    path: data/fra/dev.tsv
  - split: test
    path: data/fra/test.tsv
- config_name: hau
  data_files:
  - split: validation
    path: data/hau/val.tsv
  - split: dev
    path: data/hau/dev.tsv
  - split: test
    path: data/hau/test.tsv
- config_name: ibo
  data_files:
  - split: validation
    path: data/ibo/val.tsv
  - split: dev
    path: data/ibo/dev.tsv
  - split: test
    path: data/ibo/test.tsv
- config_name: kin
  data_files:
  - split: validation
    path: data/kin/val.tsv
  - split: dev
    path: data/kin/dev.tsv
  - split: test
    path: data/kin/test.tsv
- config_name: lin
  data_files:
  - split: validation
    path: data/lin/val.tsv
  - split: dev
    path: data/lin/dev.tsv
  - split: test
    path: data/lin/test.tsv
- config_name: lug
  data_files:
  - split: validation
    path: data/lug/val.tsv
  - split: dev
    path: data/lug/dev.tsv
  - split: test
    path: data/lug/test.tsv
- config_name: orm
  data_files:
  - split: validation
    path: data/orm/val.tsv
  - split: dev
    path: data/orm/dev.tsv
  - split: test
    path: data/orm/test.tsv
- config_name: sna
  data_files:
  - split: validation
    path: data/sna/val.tsv
  - split: dev
    path: data/sna/dev.tsv
  - split: test
    path: data/sna/test.tsv
- config_name: sot
  data_files:
  - split: validation
    path: data/sot/val.tsv
  - split: dev
    path: data/sot/dev.tsv
  - split: test
    path: data/sot/test.tsv
- config_name: swa
  data_files:
  - split: validation
    path: data/swa/val.tsv
  - split: dev
    path: data/swa/dev.tsv
  - split: test
    path: data/swa/test.tsv
- config_name: twi
  data_files:
  - split: validation
    path: data/twi/val.tsv
  - split: dev
    path: data/twi/dev.tsv
  - split: test
    path: data/twi/test.tsv
- config_name: wol
  data_files:
  - split: validation
    path: data/wol/val.tsv
  - split: dev
    path: data/wol/dev.tsv
  - split: test
    path: data/wol/test.tsv
- config_name: xho
  data_files:
  - split: validation
    path: data/xho/val.tsv
  - split: dev
    path: data/xho/dev.tsv
  - split: test
    path: data/xho/test.tsv
- config_name: yor
  data_files:
  - split: validation
    path: data/yor/val.tsv
  - split: dev
    path: data/yor/dev.tsv
  - split: test
    path: data/yor/test.tsv
- config_name: zul
  data_files:
  - split: validation
    path: data/zul/val.tsv
  - split: dev
    path: data/zul/dev.tsv
  - split: test
    path: data/zul/test.tsv
---

# Dataset Card for afrimmlu

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

AFRIMMLU is an evaluation dataset comprising translations of a subset of the MMLU dataset into 15 African languages. 
It includes test sets across all 17 languages, maintaining an English and French subsets from the original MMLU dataset. 

### Languages

There are 17 languages available :

## Dataset Structure

### Data Instances

The examples look like this for English:

```
from datasets import load_dataset
data = load_dataset('masakhane/afrimmlu', 'eng') 
# Please, specify the language code
# A data point example is below:
{
'question': 'About what percentage of the global population was literate in 1950?',
'choices': '['36%', '56%', '76%', '96%']',
'answer': 'B',
'subject': 'global_facts'
}
```

### Data Fields

- `question`: a multilingual string feature,
- `choices`: a list of 4 string features,
- `answer`: a ClassLabel feature
- `subject`: a string feature

### Data Splits

All languages has three split the `val`, `dev` and `test`, split, a subset of the original `val`, `dev` and `test` split of the MMLU dataset.

The splits have the following sizes :

| Language        | validation | dev | test |
|-----------------|-----------:|----:|-----:|
| English         |          83|   25|  500 |