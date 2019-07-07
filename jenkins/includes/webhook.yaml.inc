xml: |
  <com.tikal.hudson.plugins.notification.HudsonNotificationProperty>
    <endpoints>
      <com.tikal.hudson.plugins.notification.Endpoint>
        <protocol>HTTP</protocol>
        <format>JSON</format>
        <urlInfo>
          <urlOrId>https://linuxcontainers.org/webhook-lxcbot/</urlOrId>
          <urlType>PUBLIC</urlType>
        </urlInfo>
        <event>completed</event>
        <timeout>30000</timeout>
        <loglines>0</loglines>
        <retries>0</retries>
      </com.tikal.hudson.plugins.notification.Endpoint>
    </endpoints>
  </com.tikal.hudson.plugins.notification.HudsonNotificationProperty>
