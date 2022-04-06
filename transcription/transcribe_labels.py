### Mostly taken from https://github.com/awslabs/handwritten-text-recognition-for-apache-mxnet/blob/master/0_handwriting_ocr.ipynb

import difflib
import importlib
import math
import random
import string
import os

import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

random.seed(123)

import mxnet as mx
from skimage import transform as skimage_tf, exposure
from tqdm import tqdm

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


def get_imgsAndBoxes():
	craft_res_dir = "/projectnb/sparkgrp/ml-herbarium-grp/ml-herbarium-data/CRAFT-results/20220405-014212/"
	org_img_dir = "/projectnb/sparkgrp/ml-herbarium-grp/ml-herbarium-data/scraped-data"
	boxes = {}
	imgs = {}

	for fname in sorted(os.listdir(craft_res_dir)):
		if ".jpg" in fname and "mask" not in fname:
			# imgs.append(cv2.imread(os.path.join(craft_res_dir, fname)))
			tmp_txt = open(os.path.join(craft_res_dir, fname[:len(fname)-3]+"txt"),"r").read().split("\n")[:-1]
			tmp_txt = [line.split(",") for line in tmp_txt]
			tmp_bxs = [[[int(line[i]),int(line[i+1])] for i,val in enumerate(line) if int(i)%2==0] for line in tmp_txt ]
			boxes[fname] = (tmp_bxs)

	# get the original images to crop them
	for i in boxes:
		if ".jpeg" in fname:
			imgs.append(cv2.imread(os.path.join(org_img_dir, i), cv2.IMREAD_GRAYSCALE))

	return boxes,imgs,fnames

def get_gt():
	gt_dir = "../in_data/"
	if os.path.exists(os.path.join(gt_dir,"gt.txt")):
		gt = open(os.path.join(gt_dir,"gt.txt")).read().split("\n")
		return gt

	return None

def get_corpus():
	corpus_dir = "../in_data/"
	corpus = open(os.path.join(corpus_dir,"corpus.txt")).read().split(" ")
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
	line_crops = []
	for i,bxs in enumerate(boxes):
		img_lines = []
		for bx in bxs:
			t1,t2,t3,t4 = bx
			tmp_crop = imgs[i][t1[1]:t4[1],t1[0]:t2[0]]
			if len(tmp_crop) > 0 and len(tmp_crop[0]) > 0:
				img_lines.append(tmp_crop)
		
		line_crops.append(img_lines)
	return line_crops



### --------------------------------- Import data & process --------------------------------- ###
boxes,imgs,fnames = get_imgsAndBoxes()
corpus = get_corpus()
gt_txt = get_gt()
n_imgs = len(imgs)

# segment the lines of text (used to feed into models like mxnet)
lines = [get_lines(bxs) for bxs in boxes]
lines = [expand_boxes(bxs) for bxs in lines]
lines = crop_lines(lines, imgs)




### --------------------------------- Handwritting recognition --------------------------------- ###
handwriting_line_recognition_net = HandwritingRecognitionNet(rnn_hidden_states=512,
															 rnn_layers=2, ctx=ctx, max_seq_len=160)
pretrained_params = "models/herb_line_trained_on_all.params"
handwriting_line_recognition_net.load_parameters(pretrained_params, ctx=ctx) # "models/handwriting_line8.params"
handwriting_line_recognition_net.hybridize()


line_image_size = (60, 800)
character_probs = []
x = 0
for line_images in lines:
	form_character_prob = []
	for i, line_image in enumerate(line_images):
		# print(x,i)
		line_image = handwriting_recognition_transform(line_image, line_image_size)
		line_character_prob = handwriting_line_recognition_net(line_image.as_in_context(ctx))
		form_character_prob.append(line_character_prob)
	character_probs.append(form_character_prob)
	x+=1


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
all_decoded_am = [] # arg max
# all_decoded_bs = [] # beam search

for i, form_character_probs in enumerate(character_probs):
	# fig, axs = plt.subplots(len(form_character_probs) + 1, 
	#                         figsize=(10, int(1 + 2.3 * len(form_character_probs))))
	this_am = [] 
	# this_bs = []
	
	print("Processed img "+str(i)+" character prob")
	for j, line_character_probs in enumerate(form_character_probs):
		decoded_line_am = get_arg_max(line_character_probs)
		# print("[AM]",decoded_line_am)
		# decoded_line_bs = get_beam_search(line_character_probs)
		# decoded_line_denoiser = get_denoised(line_character_probs, ctc_bs=False)
		# print("[D ]",decoded_line_denoiser)
		
		this_am.append(decoded_line_am)
		# this_bs.append(decoded_line_bs)
		
		line_image = lines[i][j]
		# axs[j].imshow(line_image.squeeze(), cmap='Greys_r')            
		# axs[j].set_title("[AM]: {}\n[BS]: {}\n[D ]: {}\n\n".format(decoded_line_am, decoded_line_bs, decoded_line_denoiser), fontdict={"horizontalalignment":"left", "family":"monospace"}, x=0)
		# axs[j].axis('off')
	# print()
	all_decoded_am.append(this_am)
	# all_decoded_bs.append(this_bs)
	
	# axs[-1].imshow(np.zeros(shape=line_image_size), cmap='Greys_r')
	# axs[-1].axis('off')


### --------------------------------- Match words to corpus --------------------------------- ###
from difflib import get_close_matches
cnt = 0
final = []
for i,lines in enumerate(all_decoded_am):
	matched = False
	matches = []

	for j,s in enumerate(lines):
		tmp = get_close_matches(s, corpus)
		if len(tmp) != 0:
			matches.append(tmp)
#             print('am matched words img'+str(i)+':',tmp)
			matched = True
		else:
			split = s.split(" ")
			for s2 in split:
				tmp = get_close_matches(s2, corpus)
				if len(tmp) != 0:
					matches.append(tmp)
#                     print("    img"+str(i)+":", tmp)
					matched = True
#         print('bs matched words:',get_close_matches(all_decoded_bs[i][j], corpus_fullname))

	has_spaces = [label for strs in matches for label in strs if " " in label]
	if len(has_spaces) > 0: 
		# print('am matched words img'+str(i)+':',has_spaces)
		final.append(has_spaces[0])
	else: 
		# print(print('am matched words img'+str(i)+':',matches))
		final.append("-- "+str(i)+" --")

	if matched: cnt+=1
	# print()
	
# print("matched ", cnt, " out of ", len(imgs))


### --------------------------------- Determine which are same as ground truth/or just output results --------------------------------- ###
f = open("results.txt", "w")
cnt = 0
if gt_txt != None:
	for i,t in enumerate(gt_txt):
		#if i >= len(final):
	#		break
		if t == final[i]:
			print(fnames[i]+": "+t)
			f.write(fnames[i]+": "+t+"\n")
			cnt+=1
		else:
			print(fnames[i]+": N/A")
			f.write(fnames[i]+": N/A\n")

	print("acc: "+str(cnt)+"/"+str(len(gt_txt)))
	f.write("acc: "+str(cnt)+"/"+str(len(gt_txt)))
	f.close()
else:
	for i,n in enumerate(fnames):
		f.write(n+": "+final[i])
	f.close()

