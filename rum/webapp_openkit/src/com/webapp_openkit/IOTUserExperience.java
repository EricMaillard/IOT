package com.webapp_openkit;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.HashMap;

import org.apache.http.HttpEntity;
import org.apache.http.NameValuePair;
import org.apache.http.client.entity.UrlEncodedFormEntity;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.message.BasicNameValuePair;
import org.apache.http.entity.StringEntity;
import java.security.KeyManagementException;
import java.security.NoSuchAlgorithmException;
import java.security.KeyStoreException;
import org.apache.http.conn.ssl.NoopHostnameVerifier;
import org.apache.http.ssl.SSLContextBuilder;
import org.apache.http.ssl.TrustStrategy;
import java.security.cert.X509Certificate;
import java.security.cert.CertificateException;

import com.dynatrace.openkit.DynatraceOpenKitBuilder;
import com.dynatrace.openkit.api.Action;
import com.dynatrace.openkit.api.OpenKit;
import com.dynatrace.openkit.api.RootAction;
import com.dynatrace.openkit.api.Session;
import com.dynatrace.openkit.api.WebRequestTracer;

import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;
import java.util.Date;
import java.util.concurrent.TimeUnit;

import java.net.URLEncoder;
import java.time.Instant;
import java.sql.Timestamp;

import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;
import com.dynatrace.openkit.protocol.ssl.SSLBlindTrustManager;

public class IOTUserExperience {

 
  private String dynatrace_server_url = null;
  private String dynatrace_api_token = null;
  private boolean ssl_verify = true;
  private static final String accept_header_json = "application/json; charset=utf-8";
  private static final String accept_header_plain_text = "text/plain; charset=UTF-8";
  private String beaconEndpointURL = null;
  private String applicationID = null;
  private String log_sources_to_query = "";
  private String ip_address = "";
  private String device_id = "";
  private OpenKit openKit = null;
  private HashMap<String, Session> sessions = new HashMap<String, Session>();
  private ArrayList <JSONObject> previous_results = new ArrayList<JSONObject>();
  private HashMap<String, ArrayList<JSONObject>> devices_data  = new HashMap<String, ArrayList<JSONObject>>();

  public IOTUserExperience(String setting_file_path) {
    JSONParser jsonParser = new JSONParser();
    final String manufacturer = "Decathlon";
		final String applicationVersion = "1.0";
    final long deviceID = 42L;          // an ID that uniquely identifies the device
    try
    {
        //Read JSON settings file
        FileReader reader = new FileReader(setting_file_path);
        Object obj = jsonParser.parse(reader);

        JSONObject settings = (JSONObject) obj;
        this.dynatrace_server_url = (String)settings.get("dynatrace_server_url");
        this.dynatrace_api_token =  (String)settings.get("dynatrace_api_token");
        this.ssl_verify = (boolean)settings.get("ssl_verify");
        this.beaconEndpointURL = (String)settings.get("beaconEndpointURL");
        this.applicationID = (String)settings.get("applicationID");
        this.log_sources_to_query = (String)settings.get("log_sources_to_query");
        this.ip_address = (String)settings.get("ip_address");
        this.device_id = (String)settings.get("device_id");
        String operatingSystem = (String)settings.get("operating_system");
        reader.close();

        if (this.ssl_verify) {
          // create an OpenKit instance
          openKit = new DynatraceOpenKitBuilder(this.beaconEndpointURL, this.applicationID, deviceID)
              .withApplicationVersion(applicationVersion)
              .withOperatingSystem(operatingSystem)
              .build();
        }
        else {
          // create an OpenKit instance
          SSLBlindTrustManager blindTrustManager = new SSLBlindTrustManager();
          openKit = new DynatraceOpenKitBuilder(this.beaconEndpointURL, this.applicationID, deviceID)
              .withApplicationVersion(applicationVersion)
              .withOperatingSystem(operatingSystem)
              .withTrustManager(blindTrustManager)
              .build();
        }

        // we wait for OpenKit to be initialized
        // if you skip the line, OpenKit will be initialize asynchronously
        openKit.waitForInitCompletion();
    } catch (FileNotFoundException e) {
        e.printStackTrace();
    } catch (IOException e) {
        e.printStackTrace();
    } catch (ParseException e) {
        e.printStackTrace();
    }
  } 
	public static void main(String[] args) {
    IOTUserExperience iotUserExperience = new IOTUserExperience(args[0]);
    HashMap user_sessions = new HashMap();
    HashMap previous_results = new HashMap();
    try {
      while (true) {
        Date startDate = new Date();
        try {
          iotUserExperience.callLogApi();

          iotUserExperience.sendUserActions();
          Date currentDate = new Date();
          long diffInMillies = currentDate.getTime() - startDate.getTime();
          System.out.println("Wait for "+(60000 - diffInMillies)/1000+" s");
          Thread.sleep(60000 - diffInMillies);
        }
        catch (Exception e) {
          e.printStackTrace();
          Date currentDate = new Date();
          long diffInMillies = currentDate.getTime() - startDate.getTime();
          System.out.println("Wait for "+(60000 - diffInMillies)/1000+" s");
          Thread.sleep(60000 - diffInMillies);
        }
      }
    }
   catch (Exception e) {
    e.printStackTrace();
   }
	}

  
  private void callLogApi() throws IOException, ParseException {
     String uri = this.dynatrace_server_url + "/api/v2/logs/export";
     Instant querytime = Instant.now();
     Instant startTime = querytime.minusSeconds(5*60);
     long FomattedStartTime = startTime.toEpochMilli();
     long FomattedEndTime = querytime.toEpochMilli();
     // query logs to get new entry point logs
     String params = "&from="+FomattedStartTime+"&to="+FomattedEndTime+"&query="+URLEncoder.encode(this.log_sources_to_query, java.nio.charset.StandardCharsets.UTF_8.toString())+"&sort=timestamp";
     System.out.println("callLogApi params = "+params);
     ArrayList results = dynatraceGetWithNextPageKey(uri, params, "results");
     if (results == null) return;
     for (int i = 0; i < results.size(); i++) {
      JSONObject result = (JSONObject)results.get(i);
      if (!isInPreviousResults(result))
      {
        this.previous_results.add(result);
        JSONObject additionalColumns = (JSONObject)result.get("additionalColumns");
        String local_ip_address = null;
        if (additionalColumns.get(this.ip_address) != null)
        {
          JSONArray array = (JSONArray) additionalColumns.get(this.ip_address);
          local_ip_address = (String)array.get(0);
        }
        String local_device_id = null;
        if (additionalColumns.get(this.device_id) != null)
        {
          JSONArray array = (JSONArray) additionalColumns.get(this.device_id);
          local_device_id = (String)array.get(0);
        }
        String key = local_ip_address + "|" + local_device_id;
        ArrayList data = devices_data.get(key);
        if (data == null)
        {
          data = new ArrayList<JSONObject>();
          data.add(result);
          devices_data.put(key, data);
        }
        else
        {
          data.add(result);
        }
      }
    }
    // clean previous results to remove logs older that 5 minutes
    ArrayList<JSONObject> toremove = new ArrayList<JSONObject>();
    for(JSONObject jsonObject : previous_results){
        // get timestamp of object
        long timestamp =  (long)jsonObject.get("timestamp");
        Timestamp timestamp_object = new Timestamp(timestamp);
        Instant object_date = timestamp_object.toInstant();
        if (object_date.isBefore(startTime))
        {
          toremove.add(jsonObject);
        }
    }
    previous_results.removeAll(toremove);
    System.out.println("previous_results length = "+previous_results.size());

  }

  private boolean isInPreviousResults(JSONObject result)
  {
    for (int i = 0; i < this.previous_results.size(); i++) 
    {
       JSONObject current = (JSONObject)this.previous_results.get(i);
       if (current.toString().equals(result.toString())) return true; 
    }
    return false;
  }

  private void sendUserActions()  throws Exception {
    for ( String key : this.devices_data.keySet() ) {
      System.out.println("Send session data for device "+key);
      ArrayList data = (ArrayList)this.devices_data.get(key);
      Session session = this.sessions.get(key);
      if (session == null) {
        String[] separated = key.split("\\|");
        // create a new session
        System.out.println("Client IP = "+separated[0]);
        session = openKit.createSession(separated[0]);
        // identify the user
        session.identifyUser(separated[1]);
        this.sessions.put(key, session);
      }
      for (int i = 0; i < data.size(); i++) 
      {
         JSONObject current = (JSONObject)data.get(i);
         JSONObject additionalColumns = (JSONObject)current.get("additionalColumns");
         String device_model = "Unkown model";
         if (additionalColumns.get("iot.device_model") != null)
         {
            JSONArray array = (JSONArray) additionalColumns.get("iot.device_model");
            device_model = (String)array.get(0);
         }
         String device_firmware = "Unkown firmware";
         if (additionalColumns.get("iot.device_firmware") != null)
         {
          JSONArray array = (JSONArray) additionalColumns.get("iot.device_firmware");
          device_firmware = (String)array.get(0);
         }
         String device_ip = null;
         if (additionalColumns.get("iot.device_ip") != null)
         {
          JSONArray array = (JSONArray) additionalColumns.get("iot.device_ip");
          device_ip = (String)array.get(0);
         }
         String content = (String)current.get("content");
         JSONParser jsonParser = new JSONParser();
         JSONObject jsonObject = null;
         try
         { 
            jsonObject = (JSONObject)jsonParser.parse(content);
         }
         catch (ParseException e) {
             e.printStackTrace();
             throw e;
         }
         String event_type = "No event type";
         String device_type = "No device type";
         String message = null;
         String error_message = "Unknown error";
         long error_code = -1;
         if (jsonObject != null) 
         {
          event_type = (String)jsonObject.get("event_type");
          device_type = (String)jsonObject.get("device_type");
          message = (String)jsonObject.get("message");
          if (jsonObject.get("error_message") != null) error_message = (String)jsonObject.get("error_message");
          if (jsonObject.get("error_code") != null) error_code = (long)jsonObject.get("error_code");
        }
        long timestamp = -1;
        Instant object_date = null;
        timestamp =  (long)current.get("timestamp");
        if (timestamp != -1)
        {
          Timestamp timestamp_object = new Timestamp(timestamp);
          object_date = timestamp_object.toInstant();
        }
        String status =  (String)current.get("status");
        if (message != null)
        {
          System.out.println("Send user action = "+message);
          RootAction rootAction = session.enterAction(message);
          rootAction.reportValue("event_type", event_type);
          rootAction.reportValue("device_type", device_type);
          rootAction.reportValue("device_model", device_model);
          rootAction.reportValue("device_firmware", device_firmware);
          if (object_date != null)
            rootAction.reportValue("timestamp", object_date.toString());
          if (status.equals("ERROR")) {
            rootAction.reportError(error_message, Long.valueOf(error_code).intValue());            
          }
          rootAction.leaveAction();
        }
      }
      data.clear();  
    }
  }


  private ArrayList<JSONObject> dynatraceGetWithNextPageKey(String uri, String query_parameters, String array_key)  throws ParseException, IOException 
  {
    String PAGE_SIZE = "&pageSize=1000";
    String params = null;
    if (query_parameters == null)
        params = PAGE_SIZE;
    else
        params = query_parameters + PAGE_SIZE;
    // For successful API call, response code will be 200 (OK)
    ArrayList metric_list = new ArrayList<JSONObject>();
    String response = dynatraceGet(uri, params);
    if (response == null) return null;
    JSONParser jsonParser = new JSONParser();
    JSONObject jsonObject = null;
    try
    { 
       jsonObject = (JSONObject)jsonParser.parse(response);
    }
    catch (ParseException e) {
        e.printStackTrace();
        throw e;
    }
    JSONArray array = (JSONArray) jsonObject.get(array_key);
    for (int i = 0; i < array.size(); i++) {  
      JSONObject element = (JSONObject)array.get(i);
      metric_list.add(element);
    }
  
    String nextPageKey = (String)jsonObject.get("nextPageKey");
    if (nextPageKey != null)
    {
        while (true)
        {
            String NEXT_PAGE_KEY = "&nextPageKey="+nextPageKey;
            response =  dynatraceGet(uri, NEXT_PAGE_KEY);
            jsonObject = null;
            try
            { 
               jsonObject = (JSONObject)jsonParser.parse(response);
            }
            catch (ParseException e) {
                e.printStackTrace();
                throw e;
            }        
            nextPageKey = (String)jsonObject.get("nextPageKey");
            array = (JSONArray) jsonObject.get(array_key);
            for (int i = 0; i < array.size(); i++) {  
              JSONObject element = (JSONObject)array.get(i);
              metric_list.add(element);
            }
            if (nextPageKey == null)
                break;
        }
    }
    return metric_list;
  }

	private String dynatraceGet(String url, String params) throws IOException {
    CloseableHttpClient httpClient = null;
    if (this.ssl_verify){
      httpClient = HttpClients.createDefault();
    }
    else {
      httpClient = getCloseableHttpClientNoSSL();
    }
    String token_query_param = "?api-token="+this.dynatrace_api_token;
    if (params == null)
        url = url + token_query_param;
    else
      url = url + token_query_param + params;
    HttpGet httpGet = new HttpGet(url);
		httpGet.addHeader("Accept", accept_header_json);
		CloseableHttpResponse httpResponse = httpClient.execute(httpGet);

    int status_code = httpResponse.getStatusLine().getStatusCode();
		BufferedReader reader = new BufferedReader(new InputStreamReader(
				httpResponse.getEntity().getContent()));

		String inputLine;
		StringBuffer response = new StringBuffer();

		while ((inputLine = reader.readLine()) != null) {
			response.append(inputLine);
		}
		reader.close();
		// print result
		//System.out.println(response.toString());
    if (httpClient != null)
    {
      httpClient.close();
    } 
    if (status_code >= 400)
    {
      System.err.println("GET Response Status:: "
        + httpResponse.getStatusLine().getStatusCode());
      System.err.println("GET Response message:: "
        + response.toString());
      return null;
    }
    return response.toString();
	}

  public static CloseableHttpClient getCloseableHttpClientNoSSL()
  {
    CloseableHttpClient httpClient = null;
    try {
      httpClient = HttpClients.custom().
          setSSLHostnameVerifier(NoopHostnameVerifier.INSTANCE).
              setSSLContext(new SSLContextBuilder().loadTrustMaterial(null, new TrustStrategy()
              {
                  public boolean isTrusted(X509Certificate[] x509Certificates, String s) throws CertificateException
                  {
                      return true;
                  }
              }).build()).build();
    } catch (KeyManagementException e) {
      System.err.println("KeyManagementException in creating http client instance " + e);
    } catch (NoSuchAlgorithmException e) {
      System.err.println("NoSuchAlgorithmException in creating http client instance " + e);
    } catch (KeyStoreException e) {
      System.err.println("KeyStoreException in creating http client instance " + e);
    }
    return httpClient;
  }

}