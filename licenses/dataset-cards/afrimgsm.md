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
- sw
- tw
- wo
- xh
- vai
- yo
- zu
- en
- fr
multilinguality:
- multilingual
pretty_name: afrimgsm
size_categories:
- n<1K
language_details: >-
  amh, eng, ewe, fra, hau, ibo, kin, lin, lug, orm, sna, sot, swa, twi, vai, wol, xho, yor, zul
source_datasets:
- gsm8k
tags:
- afrimgsm
- afri-mgsm
- africanmgsm
task_categories:
- text2text-generation
task_ids:
- natural-language-inference
configs:
- config_name: amh
  data_files:
  - split: train
    path: data/amh/dev.tsv
  - split: test
    path: data/amh/test.tsv
- config_name: eng
  data_files:
  - split: train
    path: data/eng/dev.tsv
  - split: test
    path: data/eng/test.tsv
- config_name: ewe
  data_files:
  - split: train
    path: data/ewe/dev.tsv
  - split: test
    path: data/ewe/test.tsv
- config_name: fra
  data_files:
  - split: train
    path: data/fra/dev.tsv
  - split: test
    path: data/fra/test.tsv
- config_name: hau
  data_files:
  - split: train
    path: data/hau/dev.tsv
  - split: test
    path: data/hau/test.tsv
- config_name: ibo
  data_files:
  - split: train
    path: data/ibo/dev.tsv
  - split: test
    path: data/ibo/test.tsv
- config_name: kin
  data_files:
  - split: train
    path: data/kin/dev.tsv
  - split: test
    path: data/kin/test.tsv
- config_name: lin
  data_files:
  - split: train
    path: data/lin/dev.tsv
  - split: test
    path: data/lin/test.tsv
- config_name: lug
  data_files:
  - split: train
    path: data/lug/dev.tsv
  - split: test
    path: data/lug/test.tsv
- config_name: orm
  data_files:
  - split: train
    path: data/orm/dev.tsv
  - split: test
    path: data/orm/test.tsv
- config_name: sna
  data_files:
  - split: train
    path: data/sna/dev.tsv
  - split: test
    path: data/sna/test.tsv
- config_name: sot
  data_files:
  - split: train
    path: data/sot/dev.tsv
  - split: test
    path: data/sot/test.tsv
- config_name: swa
  data_files:
  - split: train
    path: data/swa/dev.tsv
  - split: test
    path: data/swa/test.tsv
- config_name: twi
  data_files:
  - split: train
    path: data/twi/dev.tsv
  - split: test
    path: data/twi/test.tsv
- config_name: vai
  data_files:
  - split: train
    path: data/vai/dev.tsv
  - split: test
    path: data/vai/test.tsv
- config_name: wol
  data_files:
  - split: train
    path: data/wol/dev.tsv
  - split: test
    path: data/wol/test.tsv
- config_name: xho
  data_files:
  - split: train
    path: data/xho/dev.tsv
  - split: test
    path: data/xho/test.tsv
- config_name: yor
  data_files:
  - split: train
    path: data/yor/dev.tsv
  - split: test
    path: data/yor/test.tsv
- config_name: zul
  data_files:
  - split: train
    path: data/zul/dev.tsv
  - split: test
    path: data/zul/test.tsv
---

# Dataset Card for afrimgsm

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

AFRIMGSM is an evaluation dataset comprising translations of a subset of the GSM8k dataset into 16 African languages. 
It includes test sets across all 18 languages, maintaining an English and French subsets from the original GSM8k dataset. 

### Languages

There are 18 languages available :

## Dataset Structure

### Data Instances

The examples look like this for English:

```
from datasets import load_dataset
data = load_dataset('masakhane/afrimgsm', 'eng') 
# Please, specify the language code
# A data point example is below:
{
'question': 'A football team played 22 games. They won 8 more than they lost. How many did they win?',
'answer': 15
}
```

### Data Fields

- `question`: the question string to a grade school math problem.
- `answer`: the final numeric solution.

### Data Splits

All languages has two split the `train` and `test` and they correspond with the original `train` and `test` splits of the GSM8k dataset.

The splits have the following sizes :

| Language | train | test |
|----------|------:|-----:|
| am       |     8 |  250 |
| ee       |     8 |  250 |
| ha       |     8 |  250 |
| kin      |     8 |  250 |
| ln       |     8 |  250 |
| lug      |     8 |  250 |
| orm      |     8 |  250 |
| sna      |     8 |  250 |
| sw       |     8 |  250 |
| tw       |     8 |  250 |
| vai      |     8 |  250 |
| wo       |     8 |  250 |
| xh       |     8 |  250 |
| yo       |     8 |  250 |
| zu       |     8 |  250 |
| en       |     8 |  250 |
| fr       |     8 |  250 |
