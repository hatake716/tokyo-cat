package io.github.hatake716.tokyocat;
import android.os.SystemClock;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import static io.github.hatake716.tokyocat.GameFlowTest.*;
import static io.github.hatake716.tokyocat.CatVisualTest.*;
import static org.junit.Assert.*;
@RunWith(AndroidJUnit4.class)
public class FurReviewTest {
 @Test public void fluffyCloseup() throws Exception {
  launch();
  try {
   waitFor("tokyoCatStatus().modelsReady&&tokyoCatStatus().tilesReady&&tokyoCatStatus().terrainReady",150000);
   tap("#choose-cat");revealBreed("ragdoll");tap("[data-breed='ragdoll']");tap("#close-modal");
   tap("#start");if("true".equals(js("!!document.querySelector('#tutorial-ok')")))tap("#tutorial-ok");
   JSONObject stick=new JSONObject(js("(()=>{let r=document.querySelector('#joystick').getBoundingClientRect();return {x:(r.right-8)*devicePixelRatio,y:(r.top+r.height/2)*devicePixelRatio}})()"));
   touch(android.view.MotionEvent.ACTION_DOWN,(float)stick.getDouble("x"),(float)stick.getDouble("y"));SystemClock.sleep(3500);
   touch(android.view.MotionEvent.ACTION_UP,(float)stick.getDouble("x"),(float)stick.getDouble("y"));
   tap("#camera");zoomIn();faceView(Math.PI);SystemClock.sleep(14000);screenshot("fur-front");
   String metrics=js("tokyoCatStatus().performance");
   try(FileOutputStream out=new FileOutputStream(new File(instrumentation.getTargetContext().getExternalFilesDir(null),"verification/fur-performance.json"))){out.write(metrics.getBytes(StandardCharsets.UTF_8));}
   assertTrue(new JSONObject(metrics).getDouble("fps")>0);
   faceView(Math.PI/2);screenshot("fur-side");faceView(Math.PI*.8);screenshot("fur-three-quarter");
   tap("#pose");SystemClock.sleep(1500);screenshot("fur-seated");
   assertEquals("true",js("!tokyoCatStatus().error"));
  }catch(Throwable t){screenshot("fur-failure");throw t;}finally{finish();}
 }
}
