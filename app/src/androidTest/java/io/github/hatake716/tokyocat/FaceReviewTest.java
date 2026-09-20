package io.github.hatake716.tokyocat;

import android.os.SystemClock;
import android.view.MotionEvent;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import static io.github.hatake716.tokyocat.GameFlowTest.*;
import static io.github.hatake716.tokyocat.CatVisualTest.*;
import static org.junit.Assert.*;

/** Real touch portrait review. JS reads diagnostics; it never injects a pose. */
@RunWith(AndroidJUnit4.class)
public class FaceReviewTest {
    @Test public void portraitAndBlink() throws Exception {
        launch();
        try {
            waitFor("tokyoCatStatus().modelsReady&&tokyoCatStatus().tilesReady&&tokyoCatStatus().terrainReady",150000);
            tap("#choose-cat");revealBreed("ragdoll");tap("[data-breed='ragdoll']");tap("#close-modal");
            waitFor("tokyoCatStatus().modelsReady",30000);
            tap("#start");
            if("true".equals(js("!!document.querySelector('#tutorial-ok')"))) tap("#tutorial-ok");
            JSONObject stick=new JSONObject(js("(()=>{let r=document.querySelector('#joystick').getBoundingClientRect();return {x:(r.right-8)*devicePixelRatio,y:(r.top+r.height/2)*devicePixelRatio}})()"));
            float x=(float)stick.getDouble("x"),y=(float)stick.getDouble("y");
            touch(MotionEvent.ACTION_DOWN,x,y);SystemClock.sleep(3200);touch(MotionEvent.ACTION_UP,x,y);
            tap("#camera");zoomIn();faceView(Math.PI);screenshot("face-body");
            double bodyRange=new JSONObject(js("tokyoCatStatus().camera")).getDouble("range");
            tap("#face-focus");
            assertEquals("true",js("tokyoCatStatus().camera.faceFocus"));
            SystemClock.sleep(10000);
            waitFor("tokyoCatStatus().faceAnimation.blinkTime<3",10000);
            screenshot("face-front");
            String status=js("tokyoCatStatus()");
            try(FileOutputStream out=new FileOutputStream(new File(instrumentation.getTargetContext().getExternalFilesDir(null),"verification/face-performance.json"))){out.write(status.getBytes(StandardCharsets.UTF_8));}
            assertEquals("1",js("tokyoCatStatus().faceAnimation.active"));
            boolean found=false;
            long deadline=SystemClock.uptimeMillis()+15000;
            while(SystemClock.uptimeMillis()<deadline){
                double phase=Double.parseDouble(js("tokyoCatStatus().faceAnimation.blinkTime"));
                if(phase>3.39&&phase<3.51){found=true;break;}
                SystemClock.sleep(20);
            }
            assertTrue("Blink animation must progress to closure: "+js("tokyoCatStatus().faceAnimation"),found);
            for(int i=0;i<3;i++){screenshot("face-blink-"+i);SystemClock.sleep(35);}
            faceView(Math.PI*.76);screenshot("face-three-quarter");
            faceView(Math.PI/2);screenshot("face-side");
            tap("#face-focus");assertEquals("false",js("tokyoCatStatus().camera.faceFocus"));
            assertEquals(bodyRange,new JSONObject(js("tokyoCatStatus().camera")).getDouble("range"),.001);
            assertEquals("true",js("!tokyoCatStatus().error"));
        } catch(Throwable t) {screenshot("face-failure");throw t;} finally {finish();}
    }
}
