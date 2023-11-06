from __future__ import division 
import numpy as np
import cv2,  imutils
import cmath, math

# =====================================================================

FINAL_LINE_COLOR = (255, 0, 255)
WORKING_LINE_COLOR = (255, 255, 0)
thickness = 3
lineThickness = 3
'''
W, l = 7.495, 7.03
centre = w//2,h//2
C_ = (868, 807)
B_ = (658, 581)
A_ = (517, 429)
B = (357, 617)
A = (264, 457)#
C = (1157, 357)#
D = (1410, 492)


vp1 = (-239, -381)
vp2 = (13284, -1417) 
vp3 = ( 1941,  13347)
'''# =====================================================================
#-------------------------------------------------------
def getFocal_2(vp1, vp2, pp):
    return math.sqrt(- np.dot(vp1[0:2]-pp[0:2], vp2[0:2]-pp[0:2]))


"""
Compute camera calibration from two van points and principal point
"""
def computeCameraCalibration(_vp1, _vp2, _pp):
    vp1 = np.concatenate((_vp1, [1]))    
    vp2 = np.concatenate((_vp2, [1]))    
    pp = np.concatenate((_pp, [1]))    
    focal = getFocal_2(vp1, vp2, pp)
    vp1W = np.concatenate((_vp1, [focal]))    
    vp2W = np.concatenate((_vp2, [focal]))    
    ppW = np.concatenate((_pp, [0])) 
    vp3W = np.cross(vp1W-ppW, vp2W-ppW)
    vp3 = np.concatenate((vp3W[0:2]/vp3W[2]*focal + ppW[0:2], [1]))
    vp3Direction = np.concatenate((vp3[0:2], [focal]))-ppW
    roadPlane = np.concatenate((vp3Direction/np.linalg.norm(vp3Direction), [10]))
    return vp3, roadPlane, focal

def rotate_image(s, centre, tuple_point):
    #h, w, ch = img.shape
    M = cv2.getRotationMatrix2D(centre, s, 1) 

    current = np.array( [ [tuple_point[0],tuple_point[1]] ])
    current1 = np.array([[p] for p in current])
    next = cv2.transform(current1, M)
    rotated_point = (next[0][0][0],next[0][0][1])
    return rotated_point
    
def ImageToWorld(A, centre, t, f, h):
    u = (A[0]-centre[0])
    v = (A[1]-centre[1])
    x_A = h*u/( (v +f*math.tan(t) ) * math.cos(t) )
    y_A = h*(f - v*math.tan(t))/(v+f*math.tan(t))
    return x_A, y_A
    
    
def line(p1, p2):
    A = (p1[1] - p2[1])
    B = (p2[0] - p1[0])
    C = (p1[0]*p2[1] - p2[0]*p1[1])
    return A, B, -C

def intersection(L1, L2):
    D  = L1[0] * L2[1] - L1[1] * L2[0]
    Dx = L1[2] * L2[1] - L1[1] * L2[2]
    Dy = L1[0] * L2[2] - L1[2] * L2[0]
    if D != 0:
        x = Dx / D
        y = Dy / D
        return int(x),int(y)
    else:
        return False

def Quadratic_Equation(a, b, c):
    delta = (b**2) - (4*a*c)
    solution1 = (-b-cmath.sqrt(delta))/(2*a)
    solution2 = (-b+cmath.sqrt(delta))/(2*a)
    #print('The solutions are {0} and {1}'.format(solution1,solution2))
    return solution1, solution2

def get_focal(v0, u0, W, l, A_r, B_r, C_r, D_r, centre, h, w):
    #h, w, ch = img_rotate.shape
    #h_rsz, w_rsz = 600, 900
    # projection of A-B to 'v = 0' plane 
    v_b = A_r[1] - centre[1]
    v_f = B_r[1] - centre[1]
    #v_b = C_r[1] - centre[1]
    #v_f = D_r[1] - centre[1]
    k = (v_f - v0)*(v_b - v0)/(v_f - v_b)
    L1 = line(B_r, A_r)
    L2 = line([10,h//2], centre)
    L3 = line(C_r, D_r)
    p1_gama = intersection(L1, L2)
    p2_gama = intersection(L3, L2)
    gama = np.abs(p2_gama[0] - p1_gama[0])
    #print W, l,k, gama, v0
    k_v = (gama * k * l) // (W * v0)
    #k_v_0 = v0 / (math.sin(t) * math.cos(p)**2)
    #print k_v_0, k_v
    a = 1
    b = 2*(u0**2 + v0**2) - k_v**2
    c = (u0**2 + v0**2) - (k_v**2)*(v0**2)
    s1, s2 = Quadratic_Equation(a, b, c)

    if np.sign(s1) != np.sign(s2):
        if s1 > 0:
            f = math.sqrt(np.real(s1))
        else:
            f = math.sqrt(np.real(s2))
    else:
        f = math.sqrt(np.real(s2))
    #print 'f -->' + str(f) 
        
    return f 
    
def angle_between_points( p0, p1, p2 ):
  # p1 is the center point; result is in degrees
  a = (p1[0]-p0[0])**2 + (p1[1]-p0[1])**2
  b = (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2
  c = (p2[0]-p0[0])**2 + (p2[1]-p0[1])**2
  return math.acos( (a+b-c) / math.sqrt(4*a*b) ) * 180/np.pi

def roll_angle(A, B, C, D):
    '''
    Camera calibration from road lane markings. GSK Fung, NHC Yung, 
    GKH Pang. Optical Engineering 42 (10), 2967-2978, 2003. 50, 2003
    '''
    alpha_AB = np.int64(B[0] - A[0]); beta_AB = np.int64(B[1] - A[1]); X_AB = np.int64(A[0]*B[1] - B[0]*A[1])
    alpha_AC = np.int64(C[0] - A[0]); beta_AC = np.int64(C[1] - A[1]); X_AC = np.int64(A[0]*C[1] - C[0]*A[1])
    alpha_BD = np.int64(D[0] - B[0]); beta_BD = np.int64(D[1] - B[1]); X_BD = np.int64(B[0]*D[1] - D[0]*B[1])
    alpha_CD = np.int64(D[0] - C[0]); beta_CD = np.int64(D[1] - C[1]); X_CD = np.int64(C[0]*D[1] - D[0]*C[1]) 
    
     
    
    # Optaining swig angle
    s_numi_1 = - (beta_AB * beta_AC * X_BD * alpha_CD) + (beta_AC * alpha_BD * beta_AB * X_CD)
    s_numi_2 =   (beta_CD * X_AB * beta_BD * alpha_AC) - (beta_AB * X_CD * beta_BD * alpha_AC)
    s_numi_3 = - (beta_CD * beta_BD * X_AC * alpha_AB) - (beta_AC * X_AB * alpha_BD * beta_CD)
    s_numi_4 =   (beta_AB * X_AC * beta_BD * alpha_CD) + (beta_CD * beta_AC * X_BD * alpha_AB)
    
    s_numerator = (s_numi_1 + s_numi_2 + s_numi_3 + s_numi_4)     
    s_denumi_1 = - (beta_AB * X_AC * alpha_BD * alpha_CD) + (beta_AC * X_AB * alpha_BD * alpha_CD) 
    s_denumi_2 = - (beta_AC * alpha_BD * alpha_AB * X_CD) - (alpha_AC * X_BD * beta_CD * alpha_AB)
    s_denumi_3 = - (alpha_CD * X_AB * beta_BD * alpha_AC) + (beta_AB * alpha_AC * X_BD * alpha_CD)
    s_denumi_4 = + (alpha_AB * X_CD * beta_BD * alpha_AC) + (alpha_BD * X_AC * beta_CD * alpha_AB)
    
    s_denumerator = (s_denumi_1 + s_denumi_2 + s_denumi_3 + s_denumi_4)  
    
    s = - np.arctan(s_numerator / np.float(s_denumerator)) * 180/np.pi
   
    return s

    
def sort_clockwise(points,angle):
    """
    points: (4, 2) numpy array (4 x,y points)
    angle: direction of travel in degree with respect to x-axis
    
    sort points so that:
    
		   vp1

         A         C
     vp2    
         B	        D
         <----w---->

	A,B,C,and D are four end points in 2-D image cordinates selected from a calibration pattern of rectangle ABCD
	which AB and CD are parallel to X axis in the word cordinate and BD and AC are parallel to Y axis.

    """
    #print angle
    sorted_x = points[np.argsort(points[:,0]),:]
    sorted_y = points[np.argsort(points[:,1]),:]
    #print angle
    if angle > 125 and angle < 145:        
        A = np.expand_dims(sorted_x[0,:], axis=0) # A has min x
        D = np.expand_dims(sorted_x[3,:], axis=0) # D has max x
        if (np.expand_dims(sorted_y[3,:], axis=0) == D).all():
            B = np.expand_dims(sorted_y[2,:], axis=0) # B has max y
        else:
            B = np.expand_dims(sorted_y[3,:], axis=0) # B has max y
        if (np.expand_dims(sorted_y[0,:], axis=0) == A).all():
            C = np.expand_dims(sorted_y[1,:], axis=0) # B has min y
        else:
            C = np.expand_dims(sorted_y[0,:], axis=0) # B has min y
        #print np.concatenate((A,B,C,D),axis =0)
    elif angle > 35 and angle < 55:
        B = np.expand_dims(sorted_x[0,:], axis=0) # B has min x
        C = np.expand_dims(sorted_x[3,:], axis=0) # D has max x
        
        D = np.expand_dims(sorted_y[3,:], axis=0) # B has max y
        A = np.expand_dims(sorted_y[0,:], axis=0) # B has min y
    else:
        A_C_1 = np.expand_dims(sorted_y[0,:], axis=0) # A has min y
        A_C_2 = np.expand_dims(sorted_y[1,:], axis=0) # C has max y
        if A_C_1[0][0] < A_C_2[0][0]:
            A = A_C_1
            C = A_C_2
        else:
            A = A_C_2
            C = A_C_1
        B_D_1 = np.expand_dims(sorted_y[2,:], axis=0) # A has min y
        B_D_2 = np.expand_dims(sorted_y[3,:], axis=0) # C has max y
        if B_D_1[0][0] < B_D_2[0][0]:
            B = B_D_1
            D = B_D_2
        else:
            B = B_D_2
            D = B_D_1
        A_B_angle = angle_between_points( A[0].tolist(), B[0].tolist(),
                                         [B[0][0]+10,B[0][1]] ) 
        if np.abs(A_B_angle - angle) > 40:
            A_B_1 = np.expand_dims(sorted_x[0,:], axis=0) # A has min y
            A_B_2 = np.expand_dims(sorted_x[1,:], axis=0) # C has max y
            if A_B_1[0][1] < A_B_2[0][1]:
                A = A_B_1
                B = A_B_2
            else:
                A = A_B_2
                B = A_B_1
            C_D_1 = np.expand_dims(sorted_x[2,:], axis=0) # A has min y
            C_D_2 = np.expand_dims(sorted_x[3,:], axis=0) # C has max y
            if C_D_1[0][1] < C_D_2[0][1]:
                C = C_D_1
                D = C_D_2
            else:
                C = C_D_2
                D = C_D_1            
    return np.concatenate((A,B,C,D),axis =0)
#s = swingAngle(vp1,vp2) 
    
def man_calib(points,vp1, org_shape, W, l, angle):
    '''
    Camera calibration based on:
    N. Kanhere and S. T. Birchfield. A Taxonomy and Analysis of 
    Camera Calibration Methods for Traffic. Monitoring Applications. IEEE Transactions on Intelligent Transportation Systems, 11(2): 441-452, June 2010   
    '''
    
    
    h, w = org_shape
    centre = w//2,h//2
    #h_rsz, w_rsz = rsz_shape
    sorted_points = sort_clockwise(points,angle) # Sort 'points' to find A, B, C, D
    A = tuple(sorted_points[0]); B = tuple(sorted_points[1]) 
    C = tuple(sorted_points[2]); D = tuple(sorted_points[3])
    #print points, sorted_points
    s = roll_angle(A, B, C, D); # Calculate camera roll (swing) angle
    print( 'roll angle is --> ' + str(s)) ## ch_v0r90
    '''
    Non-zero roll angle (also known as 'swing angle') can be compensated 
    by a simple image rotation
    '''
    M = cv2.getRotationMatrix2D(centre, s, 1) 

    current = np.array( [ [A[0],A[1]],[C[0],C[1]],[B[0],B[1]],
                         [D[0],D[1]],[vp1[0],vp1[1]] ])
    current1 = np.array([[p] for p in current])
    next = cv2.transform(current1, M)
    # get new posuision of A, B, C, D and vp1 after roll-angle compensation
    A_r = (next[0][0][0],next[0][0][1])
    C_r = (next[1][0][0],next[1][0][1])
    B_r = (next[2][0][0],next[2][0][1])
    D_r = (next[3][0][0],next[3][0][1])
    vp1_r = (next[4][0][0],next[4][0][1])    
    pp_r = centre 
    
    
    
    L1 = line(B_r, A_r)
    L2 = line([10,h//2], centre)
    L3 = line(C_r, D_r)
    u2 = intersection(L1, L2) # intersection of A-B and 'u = 0'
    u3 = intersection(L3, L2) # intersection of C-D and 'u = 0'
    gama = np.abs(u3[0] - u2[0]) #  #gama is the horizontal length of 
    #the projected line segment (A-C or B-D) in the image onto the v = 0 
    # axis using the first vanishing point (u0 , v0 ).

    v0, u0 = vp1_r[1]-centre[1], vp1_r[0]-centre[0]
    #f = math.sqrt(-(v0**2 + u0*u1)) # focal length
    
    f = get_focal(v0, u0, W, l, A_r, B_r, C_r, D_r, centre, h, w)
    t = math.atan(-v0/f)  # tilt angle in radian
    p = math.atan(-u0*math.cos(t)/f) # pan angle in radian
    vp2_r = []
    vp2_r.append(-(v0**2  + f**2)/u0 + centre[0])  
    vp2_r.append(v0 + centre[0]) 
    vp2 = rotate_image(-s, centre, vp2_r)
    u22 = u2[0] - centre[0]
    d = (f*math.tan(p)*math.cos(t)+u22)*W/gama
    print ('d -->' + str(d))# ch_v0r90
    
    h = f*W*math.sin(t)/(gama*math.cos(p))
    
    print( 'h -->' + str(h))# ch_v0r90
    #print 'tilt -->' + str(t * 180/np.pi), 'pan -->' + str(p * 180/np.pi)
    
    C_r_W = ImageToWorld(C_r, centre, t, f, h)
    D_r_W = ImageToWorld(D_r, centre, t, f, h)
    
    CD = math.sqrt((C_r_W[0]-D_r_W[0])**2+(C_r_W[1]-D_r_W[1])**2)
    #print 'C-D -->' + str(CD)    
    print( 'vp2 -->' + str(vp2))# ch_v0r90
    
    vp3, roadPlane, focal = computeCameraCalibration(vp1, vp2, centre)
    print( 'f --> ' + str(f)+ ' focal --> ' + str(focal))# ch_v0r90
    print( 'vp3 -->' + str(vp3[0:2]))# ch_v0r90
    return s, f, h, np.array([vp2[0],vp2[1]]),vp3[0:2], sorted_points 

    
