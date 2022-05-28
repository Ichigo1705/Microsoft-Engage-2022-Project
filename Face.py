# Making the necessary imports required
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch
from torch.utils.data import DataLoader
from torchvision import datasets
import numpy as np
import pandas as pd
import os
import cv2
from PIL import Image, ImageDraw
import sqlite3


# This function is used to capture the 21st webcam instance and return it 
def capture_image():
    
    img = cv2.VideoCapture(0)
    rescnt = 0
    while rescnt <= 20:
        if rescnt == 20:
            _, frame = img.read()
            return frame
        
        else:
            rescnt += 1

# Convert binary format to
# images or files data
def convert_data(data, file_name):
    
    with open(file_name, 'wb') as file:
        file.write(data)
    img = Image.open(file_name)
    
    return img

# Here I have defined the MTCNN architecture which I have used to detect the faces present in the image
mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20)


# Here I have defined the Residual neural network which I have used to calculated the face embeddings in a given image
resnet = InceptionResnetV1(pretrained='vggface2').eval()


face_list = []
name_list = []
embedding_list = []


# This function generates the embeddings of the images and maps them to the names present in the database
def load_face():

 con = sqlite3.connect("info.db")
 cur = con.cursor()
 data = cur.execute('''SELECT * from IMAGES;''')
 for row in data:
     name_list.append(row[0])
     image = row[1]
     img = convert_data(image, r"static\tp.jpg")
     img_aligned, prob = mtcnn(img, return_prob = True)
     
     if img_aligned is not None and prob>0.90:
         emb = resnet(img_aligned.unsqueeze(0))
         embedding_list.append(emb)
 
 con.close()
 data = [embedding_list, name_list]
 torch.save(data, 'data.pt')
 name_list.clear()
 embedding_list.clear()


# Here we have defined the function which matches the face with the recorded embeddings in the data.pt file
def face_match(img, name, id, time):
    
    temp = True

    # I load the DETAILS table from the info.db database and 
    # used it for further error detection using the input credentials from the attendance login page 
    cn = sqlite3.connect("info.db")
    cr = cn.cursor()
    s = cr.execute("SELECT col1, col2 from DETAILS;")
    s = list(s)
    data = pd.DataFrame(s, columns =['Name', 'Person id'])
    cn.close()

    # This block is used to convert the name to the format of Name Surname, i.e., JUBIN BANERJEE -> Jubin Banerjee 
    # and also to used the id
    name = name.lower()
    n = len(name)
    name1 = ""
    for i in range(0,n):
        if i==0:
            name1 += name[i].upper()
        elif name[i-1] == " ":
            name1 += name[i].upper()
        else:
            name1 += name[i]
    
    person_id = id
    
    # The mtcnn is used to extract out the face regions from the image
    face, _ = mtcnn(img, return_prob=True)
    
    # The Residual neural network is used to extract out the face embeddings after mtcnn
    emb = resnet(face.unsqueeze(0)).detach() 
    
    # Here I have loaded the data.pt file and seperated the embeddings and the names in different lists
    saved_data = torch.load('data.pt')
    embedding_list = saved_data[0] 
    name_list = saved_data[1]
    dist_list = []
    
    # I have checked the distance of the embedding emb from all the embeddings in the embedding list and 
    # the embedding with the minimum distance is the recognized name 
    for idx, emb_db in enumerate(embedding_list):
        dist = torch.dist(emb, emb_db).item()
        dist_list.append(dist)    
    idx_min = dist_list.index(min(dist_list))
    print(name_list[idx_min])
    
    # Here I have placed some conditions of updating the database entries and marking attendance
    if name1 == name_list[idx_min] and (data['Person id'][data['Name'] == name1] == person_id).bool():
     con = sqlite3.connect("info.db")
     cur = con.cursor()
     s = cur.execute('''SELECT EXISTS(SELECT 1 FROM ATTENDANCE WHERE NAME=?);''', (name1,))
     s = list(s)
     s = s[0][0]
    
     if s == 0:
        cur.execute("INSERT INTO ATTENDANCE (NAME, Status, Entry_Time) VALUES (?, ?, ?);", (name1, "Present", time))
    
     con.commit()
     con.close()
    
    else:
        temp = False
    
    return temp


# This function is used to predict the gender of the given person's image and also predict the age range as coded below
def age_gender_detect(img):
    
    # These are the pre-built model architecture that I have used for gender and age detection
    ageProto= r"Gender-and-Age-Detection-master\age_deploy.prototxt"
    ageModel= r"Gender-and-Age-Detection-master\age_net.caffemodel"
    genderProto= r"Gender-and-Age-Detection-master\gender_deploy.prototxt"
    genderModel= r"Gender-and-Age-Detection-master\gender_net.caffemodel"
    
    # Here I have defined the genders and the age list to be predicted. 
    # Also I have used some MODEL_MEAN_VALUES to get a better and sharper blob from the face image
    MODEL_MEAN_VALUES=(78.4263377603, 87.7689143744, 114.895847746)
    ageList=['(0-2)', '(4-6)', '(8-12)', '(15-20)', '(25-32)', '(38-43)', '(48-53)', '(60-100)']
    genderList=['Male','Female']
    
    # Here the models have been defined using the architectures above
    ageNet=cv2.dnn.readNet(ageModel,ageProto)
    genderNet=cv2.dnn.readNet(genderModel,genderProto)
    
    # MTCNN facial detection to pick out the face box in the image and some preprocessing before evaluation
    face, _ = mtcnn.detect(np.array(img))
    img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    padding = 20
    p = face[0]
    p = p.tolist()
    p = np.array(p, dtype = np.int32)
    facepic=img[max(0,p[1]-padding):
                   min(p[3]+padding,img.shape[0]-1),max(0,p[0]-padding)
                   :min(p[2]+padding, img.shape[1]-1)]
    
    # I have extracted out a blob from the facepic image using the cv2.dnn library for gender and age detection
    blob=cv2.dnn.blobFromImage(facepic, 1.0, (227,227), MODEL_MEAN_VALUES, swapRB=False)
    
    # Here I have assessed the blob and returned the predicted gender and age group
    genderNet.setInput(blob)
    genderPreds=genderNet.forward()
    gender=genderList[genderPreds[0].argmax()]
    ageNet.setInput(blob)
    agePreds=ageNet.forward()
    age=ageList[agePreds[0].argmax()]
    
    return gender, age

