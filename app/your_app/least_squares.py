from scipy.optimize import least_squares
import cv2, math
import numpy as np
from sklearn.metrics import mean_squared_error
from pprint import pprint
#===================================================

def rotate_image(s, centre, tuple_point):
    #h, w, ch = img.shape
    M = cv2.getRotationMatrix2D(centre, s, 1) 
    #img_rotate = cv2.warpAffine(img,M,(w,h))
    current = np.array( [ [tuple_point[0],tuple_point[1]] ])
    current1 = np.array([[p] for p in current])
    next = cv2.transform(current1, M)
    rotated_point = (next[0][0][0],next[0][0][1])
    return rotated_point

#===================================================
def ImageToWorld(A, centre, tilt, focal, height):
    u = (A[0]-centre[0])
    v = (A[1]-centre[1])
    x_A = height*u/( (v +focal*math.tan(tilt) ) * math.cos(tilt) )
    y_A = height*(focal - v*math.tan(tilt))/(v+focal*math.tan(tilt))
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
#===================================================


def loss_function(x, line_points_r, centre, v0, u0, h_is_ok, real_line_meseares, H):
    loss_ret = np.array([])
    l = line_points_r
    i = 0
    print("IT IS")
    pprint(line_points_r)
    print("done1")
    print((list(zip(l,l[1:]))[::2]))
    print("done2")
    for a,b in (list(zip(l,l[1:]))[::2]):        
        if a[1] < b[1]:
            v_b = a[1] - centre[1]
            v_f = b[1] - centre[1]
        else:
            v_b = b[1] - centre[1]
            v_f = a[1] - centre[1]
        k = (v_f - v0)*(v_b - v0)/(v_f - v_b)
        t = math.atan(-v0/x[0])
        p = math.atan(-u0*math.cos(t)/x[0])
        print("i is = " + str(i) )
        ll = (x[1]*(x[0]**2 + v0**2)/(x[0]*k*np.cos(p))) - real_line_meseares[i]
        loss_ret = np.append(loss_ret,ll)
        i = i +1
    if h_is_ok:
        loss_ret = np.append(loss_ret,x[1] - H) 
    return loss_ret
    
#===================================================
def ls_fine_tune_parameters(centre, vp1, real_line_meseares, line_points, s, x0, H, FPS_real, To_VP): # ch_v0r86 ( To_VP added)
    
    if H == 0:
        h_is_ok = 0
    else:
        h_is_ok = 1
    
    vp1_r = rotate_image(s, centre, vp1)
    v0, u0 = vp1_r[1]-centre[1], vp1_r[0]-centre[0]
    line_points_r = np.zeros(line_points.shape, int)
    for i in range(line_points.shape[0]):
        line_points_r[i,:] = rotate_image(s, centre, line_points[i,:])
    res_1 = least_squares(loss_function, x0, args=(line_points_r, centre, v0, u0, h_is_ok, real_line_meseares, H))
    
    f = res_1.x[0]
    h = res_1.x[1]
    t = math.atan(-v0/f)  # tilt angle in radian
     
    p = math.atan(-u0*math.cos(t)/f)* 180/np.pi # pan angle in radian
    print( 'f    --> ' + str(f) ,'\nh    --> ' + str(h))# ch_v0r90
    print( 'tilt --> ' + str(t * 180/np.pi),'\npan  --> ' + str(p ))# ch_v0r90
    vp2_r = []
    vp2_r.append(-(v0**2  + f**2)/u0 + centre[0])  
    vp2_r.append(v0 + centre[0]) 
    vp2 = rotate_image(-s, centre, vp2_r)
    print( 'vp1 -->' + str(vp1),'\nvp2 -->' + str(vp2))# ch_v0r90
    Tets_error = []
    l = line_points_r
    i = 0
    for a,b in list(zip(l,l[1:]))[::2]: 
        i = i + 1
        C_r_W = ImageToWorld(a, centre, t, f, h)
        D_r_W = ImageToWorld(b, centre, t, f, h)
        CD = math.sqrt((C_r_W[0]-D_r_W[0])**2+(C_r_W[1]-D_r_W[1])**2)
        print( 'L' + str(i) +'   --> ' + str(CD) + ' m')# ch_v0r90
        Tets_error.append(CD)
    """
    y_true, y_pred = np.array(real_line_meseares), np.array(Tets_error)
    print "mean_squared_error --> "+ str(mean_squared_error(real_line_meseares, Tets_error))
    print "Mean absolute percentage error (MAPE)--> "+ str( np.mean(np.abs((y_true - y_pred) / y_true)) * 100) + ' %'
    """
    M = cv2.getRotationMatrix2D(centre, s, 1)
    road_camera_staff = {'vp1': vp1, 'vp2': vp2,
                    'focal': f, 'tilt': t, 'height': h,
                    'centre': centre,'swing' : s,'FPS': FPS_real, 'RotationMatrix2D': M, 'To_VP' : To_VP, 'VP1_rsz' : 0  } # ch_v0r87 ( 'VP1_rsz' added ==> fixed bug)
    return road_camera_staff # ch_v0r82
