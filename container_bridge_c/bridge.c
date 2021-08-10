#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <netinet/in.h>
#include <linux/types.h>
#include <linux/netfilter.h>
#include <libnetfilter_queue/libnetfilter_queue.h>
#include <pthread.h>
#include <unistd.h> // Header file for sleep()
#include <time.h>
#include <errno.h>
#include <stdlib.h>  // for strtol
#include <stdbool.h>

int epr_buffer = 0; // IN QUBYTES


//Should be collected from command line arguments
int epr_frame_size = 10; // IN QUBYTES
int epr_buffer_size = 100; // IN QUBYTES
int sleep_time = 2; // IN SECONDS
int single_transmission_delay = 1; //IN MILISECONDS
bool allow_epr = true;


pthread_t tid[2];

/* msleep(): Sleep for the requested number of milliseconds. */
int msleep(long msec)
{
  struct timespec ts;
  int res;

  if (msec < 0)
    {
      errno = EINVAL;
      return -1;
    }

  ts.tv_sec =  0; //msec / 1000;
  ts.tv_nsec = msec; //(msec % 1000) * 1000000;

  do {
    res = nanosleep(&ts, &ts);
  } while (res && errno == EINTR);

  return res;
}

u_int32_t transmission_delay(int length){
  int delay;
  if(length<epr_buffer){
    printf("LENGTH < EPR_BUFFER");
    delay = length * 4;
    epr_buffer -= length;
  }else if(epr_buffer == 0){
    printf("EPR BUFFER == 0");
    delay = length * 8;
  }else{
    printf("LENGTH > EPR_BUFFER");
    delay = epr_buffer * 4 + (length-epr_buffer)*8;
    epr_buffer = 0;
  }
  delay = delay * single_transmission_delay;
  printf("The packet should be delayed for %d ms\n", delay);
  printf("Avaliable EPRs in buffer %d\n", epr_buffer);

  return delay; // Returns delay in miliseconds
}

static u_int32_t print_pkt (struct nfq_data *tb)
{
	int id = 0;
	struct nfqnl_msg_packet_hdr *ph;
	struct nfqnl_msg_packet_hw *hwph;
	u_int32_t mark,ifi; 
	int ret;
	char *data;

	ph = nfq_get_msg_packet_hdr(tb);
	if (ph) {
		id = ntohl(ph->packet_id);
		printf("hw_protocol=0x%04x hook=%u id=%u ",
			ntohs(ph->hw_protocol), ph->hook, id);
	}

	hwph = nfq_get_packet_hw(tb);
	if (hwph) {
		int i, hlen = ntohs(hwph->hw_addrlen);

		printf("hw_src_addr=");
		for (i = 0; i < hlen-1; i++)
			printf("%02x:", hwph->hw_addr[i]);
		printf("%02x ", hwph->hw_addr[hlen-1]);
	}


	ret = nfq_get_payload(tb, &data);
  printf("LENGTH=%d \n", ret);

  int delay;
  delay = transmission_delay(ret);

  printf("Delaying");
  //Should prevent from EPR Formaiton
  msleep(delay);

	fputc('\n', stdout);

	return id;
}



static int cb(struct nfq_q_handle *qh, struct nfgenmsg *nfmsg, struct nfq_data *nfa, void *data)
{
	u_int32_t id = print_pkt(nfa);
	//u_int32_t id;
  struct nfqnl_msg_packet_hdr *ph;
	ph = nfq_get_msg_packet_hdr(nfa);	
	id = ntohl(ph->packet_id);
	printf("entering callback\n");
	return nfq_set_verdict(qh, id, NF_ACCEPT, 0, NULL);
}


void *packetProcessingThread()
{
	struct nfq_handle *h;
	struct nfq_q_handle *qh;
	int fd;
	int rv;
	char buf[4096] __attribute__ ((aligned));

	printf("opening library handle\n");
	h = nfq_open();
	if (!h) {
		fprintf(stderr, "error during nfq_open()\n");
		exit(1);
	}

	printf("unbinding existing nf_queue handler for AF_INET (if any)\n");
	if (nfq_unbind_pf(h, AF_INET) < 0) {
		fprintf(stderr, "error during nfq_unbind_pf()\n");
		exit(1);
	}

	printf("binding nfnetlink_queue as nf_queue handler for AF_INET\n");
	if (nfq_bind_pf(h, AF_INET) < 0) {
		fprintf(stderr, "error during nfq_bind_pf()\n");
		exit(1);
	}

	printf("binding this socket to queue '0'\n");
	qh = nfq_create_queue(h,  0, &cb, NULL);
	if (!qh) {
		fprintf(stderr, "error during nfq_create_queue()\n");
		exit(1);
	}

	printf("setting copy_packet mode\n");
	if (nfq_set_mode(qh, NFQNL_COPY_PACKET, 0xffff) < 0) {
		fprintf(stderr, "can't set packet_copy mode\n");
		exit(1);
	}

	fd = nfq_fd(h);

	// para el tema del loss:   while ((rv = recv(fd, buf, sizeof(buf), 0)) && rv >= 0)

  // Moving processing into thread

	while ((rv = recv(fd, buf, sizeof(buf), 0)))
	{
    allow_epr = false;
		printf("pkt received\n");
		nfq_handle_packet(h, buf, rv);
    allow_epr = true;
	}

	printf("unbinding from queue 0\n");
	nfq_destroy_queue(qh);

#ifdef INSANE
	/* normally, applications SHOULD NOT issue this command, since
	 * it detaches other programs/sockets from AF_INET, too ! */
	printf("unbinding from AF_INET\n");
	nfq_unbind_pf(h, AF_INET);
#endif

	printf("closing library handle\n");
	nfq_close(h);
}

void *eprGenThread(){
  printf("Generating EPR\n");
  while(1){
    sleep(sleep_time);

    if(!allow_epr){
      printf("EPR Generation BLOCKED!");
      continue;
    }
    epr_buffer = epr_buffer + epr_frame_size;
    if(epr_buffer > epr_buffer_size){
      epr_buffer = epr_buffer_size;
    }
    printf("\nEPR BUFFER: %d/%d\n", epr_buffer, epr_buffer_size);
    fprintf(stdout, "%lu\n", (unsigned long)time(NULL)); 
  }
}

int main(int argc, char **argv)
{
  for (int i = 0; i < argc; i++) {
    printf("%s\n", argv[i]);
  }
  if(argc > 4){
    epr_frame_size = (int) strtol(argv[1], NULL, 10);
    epr_buffer_size = (int) strtol(argv[2], NULL, 10);
    sleep_time = (int) strtol(argv[3], NULL, 10);
    single_transmission_delay = (int) strtol(argv[4], NULL, 10);
  }
  printf("BRIDGE PARAMETERS ARE:\n");
  printf("epr_frame_size: %d\n", epr_frame_size);
  printf("epr_buffer_size: %d\n", epr_buffer_size);
  printf("sleep_time: %d\n", sleep_time);
  printf("single_transmission_delay: %d\n", single_transmission_delay);


  printf("Starting Packet Processing Thread\n");
  pthread_create(&(tid[0]), NULL, packetProcessingThread ,NULL);
  printf("Packet Processing Thread is Running\n");
  pthread_create(&(tid[1]), NULL, eprGenThread, NULL);
  printf("EPR generation thread is running\n");
  pthread_join(tid[0], NULL);
  pthread_join(tid[1], NULL);

	exit(0);
}
