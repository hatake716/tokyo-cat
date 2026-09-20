package io.github.hatake716.tokyocat;

import android.app.Instrumentation;
import android.graphics.Bitmap;
import android.os.SystemClock;
import android.view.MotionEvent;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.junit.runners.MethodSorters;
import java.io.File;
import java.io.FileOutputStream;
import java.util.concurrent.*;
import static org.junit.Assert.*;

/** Ordered end-to-end journey, real Android touch events, read-only JS assertions. */
@RunWith(AndroidJUnit4.class) @FixMethodOrder(MethodSorters.NAME_ASCENDING)
public class GameFlowTest {
 static ActivityScenario<MainActivity> scenario;
 static Instrumentation instrumentation;
 public static void launch() throws Exception {
  instrumentation=InstrumentationRegistry.getInstrumentation();
  scenario=ActivityScenario.launch(MainActivity.class);
  waitFor("typeof window.tokyoCatStatus==='function'",20000);
 }
 public static void finish(){ if(scenario!=null)scenario.close(); }
 static String js(String expression) throws Exception {
  CountDownLatch latch=new CountDownLatch(1);String[] value={"null"};
  scenario.onActivity(a->a.webView.evaluateJavascript(expression,r->{value[0]=r;latch.countDown();}));
  assertTrue("JS callback timeout",latch.await(12,TimeUnit.SECONDS));return value[0];
 }
 static void waitFor(String expr,long timeout) throws Exception {
  long end=SystemClock.uptimeMillis()+timeout;
  while(SystemClock.uptimeMillis()<end){if("true".equals(js(expr)))return;SystemClock.sleep(400);}
  fail("Timed out: "+expr+" status="+js("window.tokyoCatStatus?.()"));
 }
 static void tap(String selector) throws Exception {
  String q=JSONObject.quote(selector);
  waitFor("!!document.querySelector("+q+")",10000);
  JSONObject pt=new JSONObject(js("(()=>{let r=document.querySelector("+q+").getBoundingClientRect();return {x:(r.left+r.width/2)*devicePixelRatio,y:(r.top+r.height/2)*devicePixelRatio}})()"));
  int[] origin=new int[2];scenario.onActivity(a->a.webView.getLocationOnScreen(origin));
  pt.put("x",pt.getDouble("x")+origin[0]);pt.put("y",pt.getDouble("y")+origin[1]);
  touch(MotionEvent.ACTION_DOWN,(float)pt.getDouble("x"),(float)pt.getDouble("y"));
  touch(MotionEvent.ACTION_UP,(float)pt.getDouble("x"),(float)pt.getDouble("y"));SystemClock.sleep(300);
 }
 static void touch(int action,float x,float y){long now=SystemClock.uptimeMillis();MotionEvent e=MotionEvent.obtain(now,now,action,x,y,0);instrumentation.sendPointerSync(e);e.recycle();}
 static void screenshot(String name)throws Exception{Bitmap b=instrumentation.getUiAutomation().takeScreenshot();File dir=new File(instrumentation.getTargetContext().getExternalFilesDir(null),"verification");dir.mkdirs();try(FileOutputStream out=new FileOutputStream(new File(dir,name+".png"))){b.compress(Bitmap.CompressFormat.PNG,100,out);}b.recycle();}
 @Test public void completeTokyoJourney() throws Exception {
  launch();
  try {
   a01RealCityLoads(); a02LanguageSwitch(); a03TenCatsSelectable();
   a04AllDistrictsLoad(); a05DiscoveryAndGreeting(); a06WalkingChangesPosition();
   a07PhotoPersistsAndExports(); a08VisitDescriptionAndMap(); a09ProgressSurvivesActivityRecreation();
  } catch (Throwable failure) { screenshot("failure"); throw failure; } finally { finish(); }
 }
 public void a01RealCityLoads()throws Exception{waitFor("tokyoCatStatus().terrainReady && tokyoCatStatus().tilesReady && tokyoCatStatus().modelsReady",150000);assertTrue(new JSONObject(js("tokyoCatStatus().stats")).getInt("tilesLoaded")>0);screenshot("home");}
 public void a02LanguageSwitch()throws Exception{String before=js("tokyoCatStatus().lang");tap("#language");assertNotEquals(before,js("tokyoCatStatus().lang"));assertEquals("\"Start wandering  ↗\"",js("document.querySelector('#start').textContent"));screenshot("english");tap("#language");assertEquals(before,js("tokyoCatStatus().lang"));}
 public void a03TenCatsSelectable()throws Exception{tap("#choose-cat");assertEquals("10",js("document.querySelectorAll('[data-breed]').length"));tap("[data-breed='ragdoll']");waitFor("tokyoCatStatus().breed==='ragdoll'",10000);screenshot("cats");tap("#close-modal");}
 public void a04AllDistrictsLoad()throws Exception{for(String area:new String[]{"shinjuku","shibuya","akihabara","asakusa"}){tap("[data-area='"+area+"']");waitFor("tokyoCatStatus().area==='"+area+"'&&tokyoCatStatus().tilesReady&&tokyoCatStatus().modelsReady",150000);assertTrue(new JSONObject(js("tokyoCatStatus().stats")).getInt("tilesLoaded")>0);screenshot(area);}}
 public void a05DiscoveryAndGreeting()throws Exception{tap("#start");if("true".equals(js("!!document.querySelector('#tutorial-ok')")))tap("#tutorial-ok");waitFor("tokyoCatStatus().visited.includes('kaminarimon')",30000);waitFor("!document.querySelector('#greet').disabled",10000);tap("#greet");waitFor("tokyoCatStatus().friends.length>0",10000);screenshot("explore");}
 public void a06WalkingChangesPosition()throws Exception{JSONObject start=new JSONObject(js("tokyoCatStatus().position"));JSONObject pt=new JSONObject(js("(()=>{let r=document.querySelector('#joystick').getBoundingClientRect();return {x:(r.left+r.width/2)*devicePixelRatio,y:(r.top+10)*devicePixelRatio}})()"));float x=(float)pt.getDouble("x"),y=(float)pt.getDouble("y");touch(MotionEvent.ACTION_DOWN,x,y);SystemClock.sleep(3000);touch(MotionEvent.ACTION_UP,x,y);JSONObject end=new JSONObject(js("tokyoCatStatus().position"));assertTrue("Movement must change coordinates",Math.abs(start.getDouble("lat")-end.getDouble("lat"))+Math.abs(start.getDouble("lon")-end.getDouble("lon"))>0.000001);}
 public void a07PhotoPersistsAndExports()throws Exception{
  tap("#camera");waitFor("tokyoCatStatus().mode==='photo'",10000);
  tap("#pose");assertEquals("\"立つ\"",js("document.querySelector('#pose').textContent"));
  // Orbit with actual touch events, keeping clear of the camera toolbar.
  JSONObject metrics=new JSONObject(js("({w:innerWidth*devicePixelRatio,h:innerHeight*devicePixelRatio})"));
  int[] origin=new int[2];scenario.onActivity(a->a.webView.getLocationOnScreen(origin));
  float x=origin[0]+(float)metrics.getDouble("w")*.70f,y=origin[1]+(float)metrics.getDouble("h")*.45f;
  touch(MotionEvent.ACTION_DOWN,x,y);
  for(int i=1;i<=20;i++){touch(MotionEvent.ACTION_MOVE,x-i*40,y);SystemClock.sleep(20);}
  touch(MotionEvent.ACTION_UP,x-800,y);SystemClock.sleep(2000);screenshot("camera");
  tap("#shutter");waitFor("document.querySelector('#toast').textContent.includes('保存')||document.querySelector('#toast').textContent.includes('saved')",10000);
  tap("#exit-camera");tap("#open-album");tap("[data-tab='photos']");waitFor("document.querySelectorAll('[data-photo]').length>0",10000);tap("[data-photo]");tap("#export-photo");waitFor("document.querySelector('#toast').textContent.includes('Pictures/TOKYO-CAT')",15000);screenshot("photo-album");tap("#close-modal");
 }
 public void a08VisitDescriptionAndMap()throws Exception{tap("#open-album");tap("[data-place='kaminarimon']");assertTrue(new JSONArray("["+js("document.querySelector('.place-description').textContent")+"]").getString(0).length()>40);screenshot("landmark");tap("#close-modal");tap("#open-map");assertEquals("true",js("!!document.querySelector('.map-svg')"));tap("#close-modal");}
 public void a09ProgressSurvivesActivityRecreation()throws Exception{String visited=js("JSON.stringify(tokyoCatStatus().visited)"),breed=js("tokyoCatStatus().breed");scenario.recreate();waitFor("typeof tokyoCatStatus==='function' && tokyoCatStatus().modelsReady",120000);assertEquals(visited,js("JSON.stringify(tokyoCatStatus().visited)"));assertEquals(breed,js("tokyoCatStatus().breed"));tap("#home-album");tap("[data-tab='photos']");waitFor("document.querySelectorAll('[data-photo]').length>0",10000);screenshot("persistence");}
 @Test public void restoreAfterProcessRestart() throws Exception {
  launch();
  try {
   waitFor("tokyoCatStatus().modelsReady",120000);
   assertEquals("\"ragdoll\"",js("tokyoCatStatus().breed"));
   assertEquals("true",js("tokyoCatStatus().visited.includes('kaminarimon')"));
   assertEquals("true",js("tokyoCatStatus().friends.includes('asakusa-0')"));
   tap("#home-album");tap("[data-tab='photos']");
   waitFor("document.querySelectorAll('[data-photo]').length>0",10000);
   screenshot("process-restart");
  } finally { finish(); }
 }
}
