# ML-Herbarium Spring 2024 Summary Report

## 1. Overview

The Spring 2024 Team continues the machine-learning based approach to degitablize and mobilize Asian herbarium collections, our work is guided by our clients Professor Charles Davis, professor Thomas Gardos and Solution Engineer Michelle Voong (via NSF Grant [with Prof. Charles Davis](https://oeb.harvard.edu/news/herbaria-awarded-47-million-mobilize-digital-collections-asian-plant-biodiversity) and [with BU Spark!](https://oeb.harvard.edu/news/herbaria-awarded-47-million-mobilize-digital-collections-asian-plant-biodiversity)). 

We built a pipeline with commercial OCR + LLM, achieving formiddable accuracy result with over 62.3% on Taxon names, 98.5% on Collection Locations (Province/Country), 89.2% on Collector, and 80.4% on Collection Date and opened doors for potential collaborations with Chinese Virtual Herbarium (CVH).

## 2. Main Achievements

### 2.1 Pipeline and Performance

We have built a Highly accurate pipeline with sufficient benchmark testing on **1000 samples** scraped and randomly selcted from the 15,000 samples we collected from [CVH dataset](https://www.cvh.ac.cn/index.php). The performance result below leveraged Document AI and GPT-4-Turbo.

* Highly accurate
	* Taxon name: 62.3%
	* Collection locations (Province/Country): 98.5%
	* Collector name: 89.2%
	* Collection Date: 80.4%
* Cost effective:
	* 351 Min. / 1000 Samples
	* $ 66.5 / 1000 Samples 

The accuracy metrics are calculated this way:

* Taxon Accuracy metrics definition: Exact matching after both groundtruth and extraction of Taxon name are preprocessed, mainly getting rid of scholar name
Taxon name preprocessing example:  (e.g. Lysimachia fortunei Maxim. --> Lysimachia fortunei)
* Taxon Accuracy metrics explanation: There is even decrepencies between groundtruth (scraped from website) and groundtruth.
* Location Accuracy metrics definition: Exact matching of Province / Municiple name. (Required by Charles). Groundtruth also holds similar geographical granualrity, so the metrics finer granualrity (e.g. city, village, road)
* Collector Accuracy metrics definition: Exact matching of collectors. Groundtruth often hides second authors (et.al.)
* Collection Date Accuracy metrics definition: Exact matching of YYYYMMDD timestamp.

### 2.2 Benchmark

On accuracy side, while last semesters' works mainly focuses on 

* **Approach 1**: open-source models (DETR, CRAFT, TrOCR, TaxoNERD) with GBIF datasets (SU23 and prior) and 
* **Approach 2** Commercial OCR/ ViT + LLM (FA23),

but both have shown significant drawbacks. Approach 1's CV models were not fine-tuned for botantics tasks and the first step (DETR) has pruned 30% of the labeled 1,000 samples creating significant drawback on downstream tasks, while TaxoNERD (a NER model for herberia) also only performs on English texts. Approach 2 have seen significant low accuracies on Chinese and Cyrillic texts.

![png](presentation_pngs/Data_scientist_Venn_diagram.png)

On cost and time, our benchmark results:

* 351 Min. / 1000 Samples
* $ 66.5 / 1000 Samples 


The time performance was calculated under one linear thread for Document AI and GPT-4-Turbo (Input $10.00 / 1M tokens, Output $30.00 / 1M token), while one manual labeler takes around 8 ~ 16 hours and roughly $50 ~ $150 from an outsourcing service provider ([source1](https://mark.hk.cn/pricing/#), [source2](https://ai.baidu.com/support/news?action=detail&id=3192), [source3](https://scale.com/docs/rapid-faq)), while not guarantee the accuracies. 

Furthermore, if future team seek to recreate Approach 1, please refer to Refer to README.md under /trocr for detailed instructions. If problem arise (likely), please refer to the github issue or the huggingface discussions section[https://huggingface.co/spark-ds549/detr-label-detection/discussions/3].


### 2.3 CVH Scraper 

During our quest for training and validation datasets, we located Chinese Virtual Herbarium's dataset, the largest hebarium in China, collected over 10 million samples with 2.8 million samples hand-labeld by identifier over  

### 2.4 Collaboration with CVH.


## 3. 
