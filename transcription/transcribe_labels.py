### Mostly taken from https://github.com/awslabs/handwritten-text-recognition-for-apache-mxnet/blob/master/0_handwriting_ocr.ipynb

import importlib
import random
import os

import cv2

import multiprocessing as mp
from tqdm import tqdm

random.seed(123)

import mxnet as mx

# os.chdir("../mxnet/handwritten-text-recognition-for-apache-mxnet-master/")
print(os.getcwd())
# from ocr.utils.expand_bounding_box import expand_bounding_box
# from ocr.utils.sclite_helper import ScliteHelper
# from ocr.utils.word_to_line import sort_bbs_line_by_line, crop_line_images
# from ocr.utils.iam_dataset import IAMDataset, resize_image, crop_image, crop_handwriting_page
# from ocr.utils.encoder_decoder import ALPHABET, encode_char, decode_char, EOS, BOS
# from ocr.utils.beam_search import ctcBeamSearch

# import ocr.utils.denoiser_utils
import ocr.utils.beam_search

# importlib.reload(ocr.utils.denoiser_utils)
# from ocr.utils.denoiser_utils import SequenceGenerator

importlib.reload(ocr.utils.beam_search)
# from ocr.utils.beam_search import ctcBeamSearch


# from ocr.paragraph_segmentation_dcnn import SegmentationNetwork, paragraph_segmentation_transform
# from ocr.word_and_line_segmentation import SSD as WordSegmentationNet, predict_bounding_boxes
from ocr.handwriting_line_recognition import Network as HandwritingRecognitionNet, handwriting_recognition_transform
from ocr.handwriting_line_recognition import decode as decoder_handwriting, alphabet_encoding

ctx = mx.gpu(0) if mx.context.num_gpus() > 0 else mx.cpu()
NUM_CORES = min(mp.cpu_count(), 50)
craft_res_dir = "/projectnb/sparkgrp/ml-herbarium-grp/ml-herbarium-data/CRAFT-results/20220414-154031/"
org_img_dir = "/projectnb/sparkgrp/ml-herbarium-grp/ml-herbarium-data/scraped-data/20220414-143043/"

def addBox(fname):
	if ".jpg" in fname and "mask" not in fname:
		# imgs.append(cv2.imread(os.path.join(craft_res_dir, fname)))
		tmp_txt = open(os.path.join(craft_res_dir, fname[:len(fname)-3]+"txt"),"r").read().split("\n")[:-1]
		tmp_txt = [line.split(",") for line in tmp_txt]
		tmp_bxs = [[[int(line[i]),int(line[i+1])] for i,val in enumerate(line) if int(i)%2==0] for line in tmp_txt ]
		return {fname[4:len(fname)-4]: tmp_bxs}

def addImg(fIdx):
	return {fIdx: cv2.imread(os.path.join(org_img_dir, fIdx+".jpg"))}

def get_imgsAndBoxes():
	boxes = {}
	imgs = {}

	print("\nFilling boxes dictionary...")
	print("Starting multiprocessing...")
	list_imgs = sorted(os.listdir(craft_res_dir))
	pool = mp.Pool(min(mp.cpu_count(), NUM_CORES))
	for item in tqdm(pool.imap(addBox, list_imgs), total=len(sorted(os.listdir(craft_res_dir)))):
		if item: boxes.update(item)
	pool.close()
	pool.join()
	print("\nBoxes dictionary filled.\n")

	# get the original images to crop them
	print("Getting original images...")
	print("Starting multiprocessing...")
	pool = mp.Pool(min(mp.cpu_count(), NUM_CORES))
	for item in tqdm(pool.imap(addImg, boxes), total=len(boxes)):
		imgs.update(item)
	pool.close()
	pool.join()
	print("\nOriginal images obtained.\n")

	return boxes,imgs

def get_taxon_gt():
	gt_dir = org_img_dir + "taxon_gt.txt"
	if os.path.exists(os.path.join(gt_dir,"gt.txt")):
		gt = open(os.path.join(gt_dir,"gt.txt")).read().split("\n")
		ground_truth = {s.split(": ")[0]: s.split(": ")[1] for s in gt}
		return ground_truth

	return None

def get_geography_gt():
	gt_dir = org_img_dir + "geography_gt.txt"
	if os.path.exists(os.path.join(gt_dir,"gt.txt")):
		gt = open(os.path.join(gt_dir,"gt.txt")).read().split("\n")
		ground_truth = {s.split(": ")[0]: s.split(": ")[1] for s in gt}
		return ground_truth

	return None

def get_taxon_corpus():
	corpus_dir = org_img_dir + "taxon_corpus.txt"
	corpus = open(corpus_dir).read().split("\n")
	corpus = [s.lower() for s in corpus]

	corpus_fullname = [(corpus[i]+" "+corpus[i+1]) for i in range(len(corpus)-1) if (i%2==0)]
	corpus_fullname = list(set(corpus_fullname))

	corpus_full = corpus_fullname + list(set(corpus))

	return corpus_full

def get_geography_corpus():
	corpus_dir = org_img_dir + "geography_corpus.txt"
	corpus = open(corpus_dir).read().split("\n")
	corpus = [s.lower() for s in corpus]

	corpus_fullname = [(corpus[i]+" "+corpus[i+1]) for i in range(len(corpus)-1) if (i%2==0)]
	corpus_fullname = list(set(corpus_fullname))

	corpus_full = corpus_fullname + list(set(corpus))

	return corpus_full

# expands boxes according to input margins
def expand_boxes(boxes, diff_axes=False, mx=20, my=40, m=4):
	if not diff_axes:
		mx = m
		my = m
		
	boxes_exp = []
	for box in boxes:
		tl, tr, br, bl = box
		newtl = [tl[0]-mx, tl[1]-my]
		newtr = [tr[0]+mx, tr[1]-my]
		newbr = [br[0]+mx, br[1]+my]
		newbl = [bl[0]-mx, bl[1]+my]
		
		boxes_exp.append([newtl, newtr, newbr, newbl])
		
	return boxes_exp

# gets the lines of the image based on text boxes from craft
def get_lines(boxes, vert_m=12):

	newboxes = []
	oldbox = []
	i = 0

	while len(boxes) > 0:
		oldbox = boxes.pop(0)

		tbox2 = boxes.copy()
		for j,b2 in enumerate(boxes): 
			otl, otr, obr, obl = oldbox
			tl, tr, br, bl = b2

			## testing for alignment to connect boxes
			if otr[1]<=tr[1] and obr[1]>=br[1]: # vertically, new box is in range of old box
				pass
			elif otr[1]>=tr[1] and obr[1]<=br[1]: # old box in range of new box
				pass
			elif (abs(otr[1]-tr[1])<=vert_m) and (abs(obr[1]-br[1])<=vert_m): #and ((abs(otr[0]-tl[0])<=adj_m) or (abs(otl[0]-tr[0])<=adj_m)): # within range
				pass
			else:
				continue

			oldbox = [[min(otl[0],tl[0]),min(otl[1],tl[1])],[max(otr[0],tr[0]),min(otr[1],tr[1])],
					  [max(obr[0],br[0]),max(obr[1],br[1])],[min(obl[0],bl[0]),max(obl[1],bl[1])]]

			tbox2.remove(b2)
		boxes = tbox2
		newboxes.append(oldbox)
		
	return newboxes

# crops out images of the lines 
def crop_lines(boxes, imgs):
	line_crops = {}
	for key, bxs in boxes.items():
		img_lines = []
		for bx in bxs:
			t1,t2,t3,t4 = bx
			tmp_crop = imgs[key][t1[1]:t4[1],t1[0]:t2[0]]
			if len(tmp_crop) > 0 and len(tmp_crop[0]) > 0:
				img_lines.append(tmp_crop)
		line_crops[key]=img_lines
	return line_crops



### --------------------------------- Import data & process --------------------------------- ###
def import_process_data():
	boxes,imgs = get_imgsAndBoxes()
	taxon_corpus = get_taxon_corpus()
	geography_corpus = get_geography_corpus()
	taxon_gt_txt = get_taxon_gt()
	geography_gt_txt = get_geography_gt()
	
	n_imgs = len(imgs)

	# segment the lines of text (used to feed into models like mxnet)
	lines = {key: get_lines(bxs) for key, bxs in boxes.items()}
	lines = {key: expand_boxes(bxs) for key, bxs in lines.items()}
	lines = crop_lines(lines, imgs)
	return lines, taxon_corpus, geography_corpus, taxon_gt_txt, geography_gt_txt, n_imgs, boxes, imgs




### --------------------------------- Handwritting recognition --------------------------------- ###
def handwritting_recognition(lines):
	handwriting_line_recognition_net = HandwritingRecognitionNet(rnn_hidden_states=512,
																rnn_layers=2, ctx=ctx, max_seq_len=160)
	pretrained_params = "models/herb_line_trained_on_all.params"
	handwriting_line_recognition_net.load_parameters(pretrained_params, ctx=ctx) # "models/handwriting_line8.params"
	handwriting_line_recognition_net.hybridize()


	line_image_size = (60, 800)
	character_probs = {}
	for key, line_images in lines.items():
		form_character_prob = []
		for i, line_image in enumerate(line_images):
			line_image = handwriting_recognition_transform(line_image, line_image_size)
			line_character_prob = handwriting_line_recognition_net(line_image.as_in_context(ctx))
			form_character_prob.append(line_character_prob)
		character_probs[key]=form_character_prob
	return character_probs


### --------------------------------- Probability to text funcs --------------------------------- ###
def get_arg_max(prob):
	'''
	The greedy algorithm convert the output of the handwriting recognition network
	into strings.
	'''
	arg_max = prob.topk(axis=2).asnumpy()
	return decoder_handwriting(arg_max)[0]

# def get_beam_search(prob, width=5):
# 	possibilities = ctcBeamSearch(prob.softmax()[0].asnumpy(), alphabet_encoding, None, width)
# 	return possibilities[0]


### --------------------------------- Turn character probs into words --------------------------------- ###
def probs_to_words(character_probs, lines):
	all_decoded_am = {} # arg max
	# all_decoded_bs = [] # beam search

	for key, form_character_probs in character_probs.items():
		# fig, axs = plt.subplots(len(form_character_probs) + 1, 
		#                         figsize=(10, int(1 + 2.3 * len(form_character_probs))))
		this_am = [] 
		# this_bs = []
		
		print("Processed img "+str(key)+" character prob")
		for j, line_character_probs in enumerate(form_character_probs):
			decoded_line_am = get_arg_max(line_character_probs)
			# print("[AM]",decoded_line_am)
			# decoded_line_bs = get_beam_search(line_character_probs)
			# decoded_line_denoiser = get_denoised(line_character_probs, ctc_bs=False)
			# print("[D ]",decoded_line_denoiser)
			
			this_am.append(decoded_line_am)
			# this_bs.append(decoded_line_bs)
			
			line_image = lines[int(key)][j]
			# axs[j].imshow(line_image.squeeze(), cmap='Greys_r')            
			# axs[j].set_title("[AM]: {}\n[BS]: {}\n[D ]: {}\n\n".format(decoded_line_am, decoded_line_bs, decoded_line_denoiser), fontdict={"horizontalalignment":"left", "family":"monospace"}, x=0)
			# axs[j].axis('off')
		# print()
		all_decoded_am[key]=(this_am)
		# all_decoded_bs.append(this_bs)
		
		# axs[-1].imshow(np.zeros(shape=line_image_size), cmap='Greys_r')
		# axs[-1].axis('off')
		return all_decoded_am


### --------------------------------- Match words to corpus --------------------------------- ###
def match_words_to_corpus(all_decoded_am, corpus):
	from difflib import get_close_matches
	cnt = 0
	final = {}
	for key,lines in all_decoded_am:
		matched = False
		matches = []

		for key, string in lines.items():
			tmp = get_close_matches(string, corpus)
			if len(tmp) != 0:
				matches[key]=tmp
	#             print('am matched words img'+str(i)+':',tmp)
				matched = True
			else:
				split = string.split(" ")
				for s2 in split:
					tmp = get_close_matches(s2, corpus)
					if len(tmp) != 0:
						matches[key]=tmp
	#                     print("    img"+str(i)+":", tmp)
						matched = True
	#         print('bs matched words:',get_close_matches(all_decoded_bs[i][j], corpus_fullname))

		has_spaces = [label for strs in matches for label in strs if " " in label]
		if len(has_spaces) > 0: 
			# print('am matched words img'+str(i)+':',has_spaces)
			final.append(has_spaces[0])
		else: 
			# print(print('am matched words img'+str(i)+':',matches))
			final.append("-- "+str(key)+" --")

		if matched: cnt+=1
		return final
	
# print("matched ", cnt, " out of ", len(imgs))


### --------------------------------- Determine which are same as ground truth/or just output results --------------------------------- ###
def determine_match(gt, final, fname):
	f = open(fname+"_results.txt", "w")
	cnt = 0
	if gt != None:
		for key,gt in gt.items():
			if gt == final[key]:
				print(key+": "+gt)
				f.write(key+": "+gt+"\n")
				cnt+=1
			else:
				print(key+": N/A")
				f.write(key+": N/A\n")

		print("acc: "+str(cnt)+"/"+str(len(gt)))
		f.write("acc: "+str(cnt)+"/"+str(len(gt)))
		f.close()
	else:
		for key,value in final.items():
			f.write(key+": "+value)
		f.close()

def main():
	lines, taxon_corpus, geography_corpus, taxon_gt_txt, geography_gt_txt, n_imgs, boxes, imgs = import_process_data()
	character_probs = handwritting_recognition(lines)
	all_decoded_am = probs_to_words(character_probs, lines)
	taxon_final = match_words_to_corpus(all_decoded_am, taxon_corpus)
	geography_final = match_words_to_corpus(all_decoded_am, geography_corpus)
	determine_match(taxon_gt_txt, taxon_final, "taxon")
	determine_match(geography_gt_txt, geography_final, "geography")


if __name__ == "__main__":
	main()