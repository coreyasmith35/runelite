/*
 * Copyright (c) 2024, RuneLite
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
 * ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
package net.runelite.client.plugins.audiosocket;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.inject.Provides;
import java.io.IOException;
import java.io.PrintWriter;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import javax.inject.Inject;
import lombok.extern.slf4j.Slf4j;
import net.runelite.api.Actor;
import net.runelite.api.Client;
import net.runelite.api.events.AreaSoundEffectPlayed;
import net.runelite.api.events.SoundEffectPlayed;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.eventbus.Subscribe;
import net.runelite.client.plugins.Plugin;
import net.runelite.client.plugins.PluginDescriptor;

@PluginDescriptor(
	name = "Audio Socket",
	description = "Streams sound effect events over a TCP socket as JSON for external programs",
	tags = {"audio", "sound", "socket", "external"},
	enabledByDefault = false
)
@Slf4j
public class AudioSocketPlugin extends Plugin
{
	static final String CONFIG_GROUP = "audiosocket";

	@Inject
	private Client client;

	@Inject
	private AudioSocketConfig config;

	@Inject
	private Gson gson;

	private ServerSocket serverSocket;
	private Thread serverThread;
	private final List<PrintWriter> connectedClients = new CopyOnWriteArrayList<>();

	@Provides
	AudioSocketConfig provideConfig(ConfigManager configManager)
	{
		return configManager.getConfig(AudioSocketConfig.class);
	}

	@Override
	protected void startUp() throws Exception
	{
		startServer();
	}

	@Override
	protected void shutDown() throws Exception
	{
		stopServer();
	}

	private void startServer()
	{
		int port = config.port();
		serverThread = new Thread(() ->
		{
			try
			{
				serverSocket = new ServerSocket(port);
				log.info("Audio socket server listening on port {}", port);

				while (!Thread.currentThread().isInterrupted())
				{
					Socket clientSocket = serverSocket.accept();
					log.info("Audio socket client connected: {}", clientSocket.getRemoteSocketAddress());
					PrintWriter writer = new PrintWriter(clientSocket.getOutputStream(), true);
					connectedClients.add(writer);

					// Monitor client disconnection in a separate thread
					Thread monitor = new Thread(() ->
					{
						try
						{
							// Block until the client disconnects (read returns -1)
							while (clientSocket.getInputStream().read() != -1)
							{
								// discard any data sent by the client
							}
						}
						catch (IOException e)
						{
							// client disconnected
						}
						finally
						{
							connectedClients.remove(writer);
							writer.close();
							log.info("Audio socket client disconnected: {}", clientSocket.getRemoteSocketAddress());
						}
					}, "AudioSocket-Monitor");
					monitor.setDaemon(true);
					monitor.start();
				}
			}
			catch (IOException e)
			{
				if (!Thread.currentThread().isInterrupted())
				{
					log.error("Audio socket server error", e);
				}
			}
		}, "AudioSocket-Server");
		serverThread.setDaemon(true);
		serverThread.start();
	}

	private void stopServer()
	{
		if (serverThread != null)
		{
			serverThread.interrupt();
		}
		if (serverSocket != null)
		{
			try
			{
				serverSocket.close();
			}
			catch (IOException e)
			{
				log.error("Error closing audio socket server", e);
			}
		}
		for (PrintWriter writer : connectedClients)
		{
			writer.close();
		}
		connectedClients.clear();
	}

	@Subscribe
	public void onSoundEffectPlayed(SoundEffectPlayed event)
	{
		if (!config.includeSoundEffects() || connectedClients.isEmpty())
		{
			return;
		}

		JsonObject json = new JsonObject();
		json.addProperty("type", "SOUND_EFFECT");
		json.addProperty("soundId", event.getSoundId());
		json.addProperty("delay", event.getDelay());
		json.addProperty("timestamp", System.currentTimeMillis());

		Actor source = event.getSource();
		if (source != null)
		{
			json.addProperty("sourceName", source.getName());
		}

		broadcast(gson.toJson(json));
	}

	@Subscribe
	public void onAreaSoundEffectPlayed(AreaSoundEffectPlayed event)
	{
		if (!config.includeAreaSounds() || connectedClients.isEmpty())
		{
			return;
		}

		JsonObject json = new JsonObject();
		json.addProperty("type", "AREA_SOUND_EFFECT");
		json.addProperty("soundId", event.getSoundId());
		json.addProperty("sceneX", event.getSceneX());
		json.addProperty("sceneY", event.getSceneY());
		json.addProperty("range", event.getRange());
		json.addProperty("delay", event.getDelay());
		json.addProperty("timestamp", System.currentTimeMillis());

		Actor source = event.getSource();
		if (source != null)
		{
			json.addProperty("sourceName", source.getName());
		}

		broadcast(gson.toJson(json));
	}

	private void broadcast(String message)
	{
		for (PrintWriter writer : connectedClients)
		{
			writer.println(message);
			if (writer.checkError())
			{
				connectedClients.remove(writer);
			}
		}
	}
}
