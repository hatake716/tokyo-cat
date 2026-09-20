package io.github.hatake716.tokyocat;

import android.os.SystemClock;
import android.view.MotionEvent;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;
import static io.github.hatake716.tokyocat.GameFlowTest.*;
import static org.junit.Assert.*;

/** Native touch-driven closeups for visual review; state is only read by JS. */
@RunWith(AndroidJUnit4.class)
public class CatVisualTest {
 static void orbit(float cssDx) throws Exception {
  JSONObject m=new JSONObject(js("({w:innerWidth*devicePixelRatio,h:innerHeight*devicePixelRatio,d:devicePixelRatio})"));
  float x=(float)m.getDouble("w")*.70f,y=(float)m.getDouble("h")*.48f,delta=cssDx*(float)m.getDouble("d");
  touch(MotionEvent.ACTION_DOWN,x,y);
  for(int i=1;i<=12;i++){touch(MotionEvent.ACTION_MOVE,x+delta*i/12,y);SystemClock.sleep(20);}
  touch(MotionEvent.ACTION_UP,x+delta,y);SystemClock.sleep(350);
 }
 static void zoomIn() throws Exception {
  JSONObject r=new JSONObject(js("(()=>{let r=document.querySelector('#photo-distance').getBoundingClientRect();return {x:(r.left+2+r.width*.13)*devicePixelRatio,y:(r.top+r.height/2)*devicePixelRatio}})()"));
  touch(MotionEvent.ACTION_DOWN,(float)r.getDouble("x"),(float)r.getDouble("y"));
  touch(MotionEvent.ACTION_UP,(float)r.getDouble("x"),(float)r.getDouble("y"));SystemClock.sleep(350);
 }
 static void faceView(double angle) throws Exception {
  JSONObject status=new JSONObject(js("tokyoCatStatus()"));
  double desired=status.getJSONObject("position").getDouble("heading")+angle;
  double delta=Math.atan2(Math.sin(desired-status.getJSONObject("camera").getDouble("yaw")),Math.cos(desired-status.getJSONObject("camera").getDouble("yaw")));
  // Split large rotations to keep each touch inside the WebView.
  while(Math.abs(delta)>.001){double step=Math.max(-1.0,Math.min(1.0,delta));orbit((float)(-step/.006));delta-=step;}
 }
 static void revealBreed(String breed) throws Exception {
  for(int attempt=0;attempt<4;attempt++) {
   JSONObject r=new JSONObject(js("(()=>{let r=document.querySelector('[data-breed=\""+breed+"\"]').getBoundingClientRect();return {y:r.top+r.height/2,h:innerHeight,w:innerWidth,d:devicePixelRatio}})()"));
   if(r.getDouble("y")>70&&r.getDouble("y")<r.getDouble("h")-40)return;
   float x=(float)(r.getDouble("w")*.55*r.getDouble("d")),y=(float)(r.getDouble("h")*.72*r.getDouble("d")),delta=(float)(r.getDouble("h")*.4*r.getDouble("d"));
   touch(MotionEvent.ACTION_DOWN,x,y);
   for(int i=1;i<=20;i++){touch(MotionEvent.ACTION_MOVE,x,y-delta*i/20);SystemClock.sleep(20);}
   touch(MotionEvent.ACTION_UP,x,y-delta);SystemClock.sleep(350);
  }
 }
 @Test public void inspectCatsAndMovement() throws Exception {
  launch();
  try {
   waitFor("tokyoCatStatus().modelsReady&&tokyoCatStatus().tilesReady&&tokyoCatStatus().terrainReady",150000);
   // Move away from the friendly spawn cat before closeup framing.
   tap("#start");if("true".equals(js("!!document.querySelector('#tutorial-ok')")))tap("#tutorial-ok");
   JSONObject stick=new JSONObject(js("(()=>{let r=document.querySelector('#joystick').getBoundingClientRect();return {x:(r.right-8)*devicePixelRatio,y:(r.top+r.height/2)*devicePixelRatio}})()"));
   touch(MotionEvent.ACTION_DOWN,(float)stick.getDouble("x"),(float)stick.getDouble("y"));SystemClock.sleep(2800);
   touch(MotionEvent.ACTION_UP,(float)stick.getDouble("x"),(float)stick.getDouble("y"));tap("#home-button");
   for(String breed:new String[]{"mixed","scottish","munchkin","minuet","siberian","british","american","norwegian","ragamuffin","ragdoll"}) {
    tap("#choose-cat");revealBreed(breed);tap("[data-breed='"+breed+"']");tap("#close-modal");
    waitFor("tokyoCatStatus().modelsReady&&tokyoCatStatus().breed==='"+breed+"'",30000);
    tap("#start");if("true".equals(js("!!document.querySelector('#tutorial-ok')")))tap("#tutorial-ok");
    tap("#camera");zoomIn();faceView(Math.PI/2);screenshot("cat-"+breed+"-side");faceView(Math.PI);screenshot("cat-"+breed+"-front");
    tap("#pose");SystemClock.sleep(1300);screenshot("cat-"+breed+"-sit");
    tap("#exit-camera");tap("#home-button");
   }
   tap("#start");
   JSONObject pt=new JSONObject(js("(()=>{let r=document.querySelector('#joystick').getBoundingClientRect();return {x:(r.left+r.width/2)*devicePixelRatio,y:(r.top+10)*devicePixelRatio}})()"));
   float x=(float)pt.getDouble("x"),y=(float)pt.getDouble("y");
   for(String gait:new String[]{"walk","run"}) {
    if(gait.equals("run"))tap("#run");
    touch(MotionEvent.ACTION_DOWN,x,y);
    for(int i=0;i<8;i++){SystemClock.sleep(180);screenshot("motion-"+gait+"-"+i);}
    touch(MotionEvent.ACTION_UP,x,y);SystemClock.sleep(800);screenshot("motion-"+gait+"-stop");
   }
   assertEquals("true",js("!tokyoCatStatus().error"));
  } catch(Throwable failure) {screenshot("cat-review-failure");throw failure;} finally {finish();}
 }
 @Test public void photoPausesNpcLocomotion() throws Exception {
  launch();
  try {
   waitFor("tokyoCatStatus().modelsReady&&tokyoCatStatus().tilesReady",150000);
   tap("#start");if("true".equals(js("!!document.querySelector('#tutorial-ok')")))tap("#tutorial-ok");
   waitFor("tokyoCatStatus().npcAnimation.some(v=>v>.2)",20000);
   tap("#camera");
   waitFor("tokyoCatStatus().npcAnimation.every(v=>v<.001)",10000);
   SystemClock.sleep(500);
   assertEquals("true",js("tokyoCatStatus().npcAnimation.every(v=>v<.001)"));
  } finally {finish();}
 }

}
